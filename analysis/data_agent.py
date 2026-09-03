"""校园一卡通 AI 数据分析 Agent（第 6 步：Agent 扩展）。

原理：模型不直接编造数字，而是：
    1. 理解用户的中文问题
    2. 决定调用哪个"工具"（pandas 统计函数）
    3. 拿到工具返回的真实结果后，组织成最终回答

这就是最小可用的 AI Agent：大模型负责规划，代码负责执行，结果可验证。

运行方式（需要先配置 ZHIPU_API_KEY）：
    python analysis/data_agent.py --question "哪个商户营业额最高？"

不带参数运行会进入交互问答模式，输入"退出"结束。
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

# 模型可用环境变量覆盖，默认与已验证可用的智谱模型保持一致
MODEL = os.environ.get("DATA_AGENT_MODEL", "glm-4.6v")
MAX_STEPS = 6  # 最多让模型调用 6 轮工具，防止死循环


# ---------------- 数据加载与工具实现 ----------------

_CACHE: dict[str, pd.DataFrame] = {}


def load_frame() -> pd.DataFrame:
    """读取清洗后流水并合并学生表（只读一次，后续工具共用）。"""
    if "frame" in _CACHE:
        return _CACHE["frame"]
    transactions = pd.read_csv(
        DATA_DIR / "clean_transactions.csv", dtype={"student_id": "string"}
    )
    students = pd.read_csv(DATA_DIR / "student_info.csv", dtype={"student_id": "string"})
    frame = transactions.merge(students, on="student_id", how="left")
    frame["datetime"] = pd.to_datetime(frame["date"].astype(str) + " " + frame["time"])
    frame["hour"] = frame["datetime"].dt.hour
    _CACHE["frame"] = frame
    return frame


def tool_overview() -> str:
    """总览：数据规模、总营业额、平均单笔、人均日消费等。"""
    frame = load_frame()
    students = pd.read_csv(DATA_DIR / "student_info.csv", dtype={"student_id": "string"})
    n_days = frame["date"].nunique()
    total = frame["amount"].sum()
    return (
        f"共 {len(frame)} 笔消费，覆盖 {frame['student_id'].nunique()} 名学生、"
        f"{n_days} 天；总营业额 {total:.2f} 元；平均单笔 {frame['amount'].mean():.2f} 元；"
        f"整体人均日消费 {total / (len(students) * n_days):.2f} 元。"
    )


def tool_hourly_peak() -> str:
    """各时段（小时）消费笔数排序。"""
    frame = load_frame()
    hourly = frame["hour"].value_counts().sort_values(ascending=False)
    lines = ["各小时消费笔数 TOP5："]
    lines += [f"- {hour} 点：{count} 笔" for hour, count in hourly.head(5).items()]
    return "\n".join(lines)


def tool_merchant_revenue(top_n: int = 5) -> str:
    """按商户汇总营业额，返回营业额最高的 top_n 个商户。"""
    frame = load_frame()
    revenue = (
        frame.groupby("merchant", as_index=False)["amount"]
        .sum()
        .sort_values("amount", ascending=False)
        .head(top_n)
    )
    lines = [f"营业额最高的 {len(revenue)} 个商户："]
    lines += [f"- {row.merchant}：{row.amount:.2f} 元" for row in revenue.itertuples(index=False)]
    return "\n".join(lines)


def tool_category_revenue() -> str:
    """按品类（食堂/超市/饮品）汇总营业额及占比。"""
    frame = load_frame()
    total = frame["amount"].sum()
    revenue = frame.groupby("category")["amount"].sum().sort_values(ascending=False)
    lines = ["各品类营业额与占比："]
    lines += [f"- {name}：{value:.2f} 元（{value / total:.1%}）" for name, value in revenue.items()]
    return "\n".join(lines)


def tool_college_per_capita() -> str:
    """各学院学生人均日消费对比。"""
    frame = load_frame()
    students = pd.read_csv(DATA_DIR / "student_info.csv", dtype={"student_id": "string"})
    n_days = frame["date"].nunique()
    college_amount = frame.groupby("college")["amount"].sum()
    college_count = students.groupby("college").size()
    per_capita = (college_amount / (college_count * n_days)).sort_values(ascending=False)
    lines = ["各学院人均日消费（元）："]
    lines += [f"- {name}：{value:.2f}" for name, value in per_capita.items()]
    return "\n".join(lines)


def tool_grade_per_capita() -> str:
    """各年级（2022-2025）学生人均日消费对比。"""
    frame = load_frame()
    students = pd.read_csv(DATA_DIR / "student_info.csv", dtype={"student_id": "string"})
    n_days = frame["date"].nunique()
    grade_amount = frame.groupby("grade")["amount"].sum()
    grade_count = students.groupby("grade").size()
    per_capita = (grade_amount / (grade_count * n_days)).sort_values(ascending=False)
    lines = ["各年级人均日消费（元）："]
    lines += [f"- {int(name)} 级：{value:.2f}" for name, value in per_capita.items()]
    return "\n".join(lines)


def tool_gender_per_capita() -> str:
    """男/女学生人均日消费对比。"""
    frame = load_frame()
    students = pd.read_csv(DATA_DIR / "student_info.csv", dtype={"student_id": "string"})
    n_days = frame["date"].nunique()
    gender_amount = frame.groupby("gender")["amount"].sum()
    gender_count = students.groupby("gender").size()
    per_capita = (gender_amount / (gender_count * n_days)).sort_values(ascending=False)
    lines = ["各性别学生人均日消费（元）："]
    lines += [f"- {name}：{value:.2f}" for name, value in per_capita.items()]
    return "\n".join(lines)


def tool_student_profile(student_id: str) -> str:
    """单个学生画像：总消费、有效天数、日均消费、常去商户、高峰时段等。"""
    frame = load_frame()
    sid = str(student_id).strip()
    sub = frame[frame["student_id"].astype(str) == sid]
    if sub.empty:
        return "未找到该学号记录，请让用户确认学号是否输入正确。"

    total = sub["amount"].sum()
    n_tx = len(sub)
    active_days = sub["date"].nunique()
    top_merchants = (
        sub.groupby("merchant")["amount"].sum().sort_values(ascending=False).head(3)
    )
    top_hours = sub["hour"].value_counts().head(3)
    lines = [
        f"学生 {sid} 画像：3 周总消费 {total:.2f} 元，共 {n_tx} 笔，"
        f"有效消费 {active_days} 天，日均 {total / active_days:.2f} 元。",
        "常去商户：" + "、".join(f"{name}（{value:.0f} 元）" for name, value in top_merchants.items()),
        "高频时段：" + "、".join(f"{hour} 点（{count} 次）" for hour, count in top_hours.items()),
    ]
    return "\n".join(lines)


def tool_low_consumption() -> str:
    """经常刷卡但日均消费最低的候选学生数量与示例（学号打码）。"""
    frame = load_frame()
    per_student = (
        frame.groupby("student_id")
        .agg(total_spend=("amount", "sum"), active_days=("date", "nunique"))
        .reset_index()
    )
    per_student["avg_daily"] = per_student["total_spend"] / per_student["active_days"]
    median_days = per_student["active_days"].median()
    frequent = per_student[per_student["active_days"] >= median_days]
    threshold = frequent["avg_daily"].quantile(0.10)
    candidates = frequent[frequent["avg_daily"] <= threshold]

    def mask(sid: str) -> str:
        sid = str(sid)
        return sid[:4] + "****" + sid[-2:] if len(sid) >= 6 else sid + "****"

    lines = [
        f"低消费候选共 {len(candidates)} 人（阈值：日均 ≤ {threshold:.2f} 元），示例："
    ]
    lines += [
        f"- {mask(row.student_id)}：日均 {row.avg_daily:.2f} 元"
        for row in candidates.sort_values("avg_daily").head(3).itertuples(index=False)
    ]
    lines.append("注意：仅为初步筛查，需人工复核，不能给学生贴标签。")
    return "\n".join(lines)


# 工具注册表：名字 -> (函数, 参数说明)
TOOL_MAP = {
    "get_overview": tool_overview,
    "get_hourly_peak": tool_hourly_peak,
    "get_merchant_revenue": tool_merchant_revenue,
    "get_category_revenue": tool_category_revenue,
    "get_college_per_capita": tool_college_per_capita,
    "get_grade_per_capita": tool_grade_per_capita,
    "get_gender_per_capita": tool_gender_per_capita,
    "get_student_profile": tool_student_profile,
    "get_low_consumption_candidates": tool_low_consumption,
}

# 某些工具对应的现成图表：Agent 用过该工具后，会在回答末尾附上相关图
CHART_FOR_TOOL = {
    "get_hourly_peak": "reports/hourly_activity.png",
    "get_merchant_revenue": "reports/merchant_revenue.png",
    "get_college_per_capita": "reports/college_per_capita.png",
}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_overview",
            "description": "获取数据总览：总营业额、笔数、人均日消费等",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_hourly_peak",
            "description": "获取各小时消费笔数，用于回答消费高峰问题",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_merchant_revenue",
            "description": "获取营业额最高的商户列表",
            "parameters": {
                "type": "object",
                "properties": {
                    "top_n": {
                        "type": "integer",
                        "description": "返回几个商户，默认 5",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_category_revenue",
            "description": "获取食堂/超市/饮品等品类的营业额与占比",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_college_per_capita",
            "description": "获取各学院学生人均日消费",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_grade_per_capita",
            "description": "获取各年级学生人均日消费",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_gender_per_capita",
            "description": "获取男、女学生人均日消费",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_student_profile",
            "description": "获取单个学生的消费画像，需要用户提供完整学号",
            "parameters": {
                "type": "object",
                "properties": {
                    "student_id": {
                        "type": "string",
                        "description": "学生完整学号，例如 20230001",
                    }
                },
                "required": ["student_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_low_consumption_candidates",
            "description": "获取低消费候选学生数量与示例",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

SYSTEM_PROMPT = (
    "你是校园一卡通数据的分析助手。规则：\n"
    "1. 回答消费类问题前必须先调用可用工具获取真实数据，严禁编造数字。\n"
    "2. 需要多个维度时，可以按顺序调用多个工具。\n"
    "3. 用简洁中文回答，列出关键数字；涉及名单时提醒这是初步筛查结果。\n"
    "4. 如果问题超出工具能回答的范围，直接说明能力边界，不要猜测。\n"
    f"数据为模拟数据：120 名学生、2026-03-02 至 2026-03-22。"
)


# ---------------- Agent 主循环 ----------------

def make_client():
    """延迟导入并创建智谱客户端。"""
    from zai import ZhipuAiClient

    api_key = os.environ.get("ZHIPU_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("缺少 ZHIPU_API_KEY：请先设置智谱 API Key")
    return ZhipuAiClient(api_key=api_key)


def call_model(client, messages: list[dict]) -> object:
    """调用一次模型，返回响应对象。"""
    return client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOL_SCHEMAS,
        temperature=0.1,
        timeout=90,
    )


def ask(client, question: str, show_trace: bool = False) -> str:
    """执行 Agent 循环：模型规划 -> 工具执行 -> 再让模型总结。"""
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    used_charts: list[str] = []  # 记录本轮实际用到的相关图表

    def finalize(text: str) -> str:
        """在文字回答末尾附上真实调用过工具对应的图表。"""
        if not text or not used_charts:
            return text
        lines = [text, "", "## 相关图表", ""]
        for chart in used_charts:
            caption = Path(chart).stem
            lines.append(f"![{caption}]({chart})")
        return "\n".join(lines)

    for step in range(MAX_STEPS):
        response = call_model(client, messages)
        message = response.choices[0].message

        if not getattr(message, "tool_calls", None):
            return finalize(message.content or "（模型没有返回文字）")

        # 把模型要求调用的工具消息加入历史
        assistant_msg: dict = {
            "role": message.role or "assistant",
            "content": message.content,
        }
        tool_calls = []
        for tc in message.tool_calls:
            tool_calls.append(
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
            )
            if show_trace:
                print(f"[Agent] 第 {step + 1} 轮调用工具：{tc.function.name}")
        assistant_msg["tool_calls"] = tool_calls
        messages.append(assistant_msg)

        # 逐个执行工具，把真实结果作为 tool 消息返回给模型
        for tc in message.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
                result = TOOL_MAP[name](**args)
            except Exception as exc:  # 工具异常也要如实回传，不让模型乱编
                result = f"工具执行失败：{exc}"
            chart = CHART_FOR_TOOL.get(name)
            if chart and (ROOT / chart).exists() and chart not in used_charts:
                used_charts.append(chart)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(result),
                }
            )

    # 达到最大轮数仍没结束：要求模型基于已有工具结果做最终回答
    messages.append(
        {
            "role": "user",
            "content": "请基于前面工具返回的结果直接给出最终中文回答。",
        }
    )
    response = call_model(client, messages)
    return finalize(response.choices[0].message.content or "（未能生成最终回答）")


def main() -> None:
    parser = argparse.ArgumentParser(description="校园一卡通 AI 数据分析 Agent")
    parser.add_argument("--question", help="要问的问题；不填则进入交互模式")
    parser.add_argument("--trace", action="store_true", help="打印每一步调用了哪些工具")
    args = parser.parse_args()

    client = make_client()
    if args.question:
        print(ask(client, args.question, show_trace=args.trace))
        return

    print("校园一卡通 AI 数据分析助手（输入 退出 结束）")
    while True:
        question = input("你问：").strip()
        if not question:
            continue
        if question in {"退出", "quit", "exit"}:
            print("再见！")
            break
        print(ask(client, question, show_trace=args.trace))
        print()


if __name__ == "__main__":
    main()
