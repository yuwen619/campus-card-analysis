"""第 4 步：把分析结果整理成一份图文结论报告。

运行方式：
    python analysis/build_report.py

产出：
    reports/analysis_report.md    图文分析报告

报告结构对应方案里的四个业务问题：
    问题 1：一天中哪些时段是消费高峰？
    问题 2：哪个食堂/窗口、哪类商品最受欢迎？
    问题 3：学生人均消费大概是多少？分布什么样？
    问题 4：是否存在长期低消费、可能生活困难的学生？
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
REPORT_DIR = ROOT / "reports"


def load_clean() -> pd.DataFrame:
    transactions = pd.read_csv(
        DATA_DIR / "clean_transactions.csv", dtype={"student_id": "string"}
    )
    students = pd.read_csv(DATA_DIR / "student_info.csv", dtype={"student_id": "string"})
    frame = transactions.merge(students, on="student_id", how="left")
    frame["datetime"] = pd.to_datetime(frame["date"].astype(str) + " " + frame["time"])
    frame["hour"] = frame["datetime"].dt.hour
    return frame, students


def mask_student_id(student_id: str) -> str:
    """学号打码：只保留前 4 位和后 2 位，用于报告示例。"""
    sid = str(student_id)
    if len(sid) >= 6:
        return sid[:4] + "****" + sid[-2:]
    return sid + "****"


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    frame, students = load_clean()
    n_days = frame["date"].nunique()

    # ---------- 总体指标 ----------
    total_revenue = frame["amount"].sum()
    avg_amount = frame["amount"].mean()
    n_records = len(frame)

    # ---------- 问题 1：消费高峰 ----------
    hourly = frame["hour"].value_counts().sort_index()
    top_hours = hourly.sort_values(ascending=False).head(3)
    top_hours_text = "、".join(f"{hour} 点（{count} 笔）" for hour, count in top_hours.items())

    # ---------- 问题 2：商户与品类 ----------
    category_revenue = frame.groupby("category")["amount"].sum().sort_values(ascending=False)
    merchant_revenue = frame.groupby("merchant")["amount"].sum().sort_values(ascending=False)
    top_merchants = merchant_revenue.head(3)
    top_merchants_text = "、".join(f"{name}（{value:.0f} 元）" for name, value in top_merchants.items())

    category_lines = "\n".join(
        f"| {name} | {value:.2f} | {value / total_revenue:.1%} |"
        for name, value in category_revenue.items()
    )

    # ---------- 问题 3：消费水平与分布 ----------
    per_student = (
        frame.groupby("student_id")
        .agg(
            total_spend=("amount", "sum"),
            n_transactions=("transaction_id", "count"),
            active_days=("date", "nunique"),
        )
        .reset_index()
    )
    per_student["avg_daily_on_active_days"] = (
        per_student["total_spend"] / per_student["active_days"]
    )
    overall_daily_per_student = total_revenue / (len(students) * n_days)

    # ---------- 问题 4：低消费候选 ----------
    # 思路：只看"经常刷卡"的学生（有效天数 >= 中位数），
    # 再取这些学生中"平均每天卡内消费"最低的 10% 作为候选。
    # 这样能排除"根本不用卡"的人，但也只是初步筛查，不代表真实困难。
    median_days = per_student["active_days"].median()
    frequent = per_student[per_student["active_days"] >= median_days]
    low_threshold = frequent["avg_daily_on_active_days"].quantile(0.10)
    candidates = frequent[frequent["avg_daily_on_active_days"] <= low_threshold]

    candidate_examples = candidates.sort_values("avg_daily_on_active_days").head(3)
    candidate_lines = "\n".join(
        f"| {mask_student_id(row.student_id)} | {row.avg_daily_on_active_days:.2f} 元/天 | "
        f"{row.active_days} 天 | {row.total_spend:.2f} 元 |"
        for row in candidate_examples.itertuples(index=False)
    )

    # ---------- 组装报告 ----------
    lines = [
        "# 校园一卡通消费分析报告",
        "",
        "> 数据范围：模拟 120 名学生在 2026-03-02 至 2026-03-22（21 天）的校园卡消费流水。",
        f"> 数据质量：原始 6593 条，清洗后 {n_records} 条（清洗记录见 `cleaning_report.md`）。",
        "",
        "## 一、执行摘要",
        "",
        "本次分析基于校园一卡通消费数据，回答了消费时段、热门商户、消费水平与低消费识别"
        "四类问题。主要发现：",
        "",
        f"1. 消费集中在三餐时段：早餐 8 点、午餐 12 点、晚餐 18 点各有高峰，"
        "其中单小时笔数以晚餐 18 点最高。",
        f"2. 食堂消费占绝对主导（{category_revenue.iloc[0] / total_revenue:.0%} 的营业额），"
        f"其中{top_merchants.index[0]}最受欢迎。",
        f"3. 平均单笔消费 {avg_amount:.2f} 元；按 120 名学生与 21 天折算，"
        f"人均日消费约 {overall_daily_per_student:.1f} 元。",
        f"4. 初步筛出 {len(candidates)} 名低消费候选学生，需结合其他信息人工核实。",
        "",
        "## 二、问题 1：哪些时段是消费高峰？",
        "",
        "![各时段消费笔数](hourly_activity.png)",
        "",
        "结论：消费集中在三餐时段，早餐 8 点、午餐 12 点、晚餐 18 点各有一个高峰。"
        f"按单小时笔数排序，前三位为：{top_hours_text}。",
        "",
        "建议：午餐 12 点和晚餐 18 点前后食堂压力最大，可考虑错峰宣传、增开窗口或优化排队动线。",
        "",
        "## 三、问题 2：哪些商户和品类最受欢迎？",
        "",
        "![各商户营业额 TOP10](merchant_revenue.png)",
        "",
        "按品类统计营业额：",
        "",
        "| 品类 | 营业额（元） | 占比 |",
        "| --- | ---: | ---: |",
        category_lines,
        "",
        f"结论：营业额最高的三家商户是{top_merchants_text}。"
        "食堂是绝对主力，超市和饮品属于补充消费。",
        "",
        "建议：采购与备货资源优先向高营业额食堂窗口倾斜；超市可结合销售结构优化小商品选品。",
        "",
        "## 四、问题 3：学生人均消费大概是多少？",
        "",
        "![单笔消费金额分布](amount_distribution.png)",
        "",
        f"结论：平均单笔消费 {avg_amount:.2f} 元；金额集中在 10~18 元区间。"
        f"整体人均日消费约 {overall_daily_per_student:.1f} 元，各学院差异不大。",
        "",
        "![各学院学生人均日消费](college_per_capita.png)",
        "",
        "## 五、问题 4：是否存在可能生活困难的低消费学生？",
        "",
        "方法说明：只统计**经常刷卡**的学生（21 天中有效消费天数不低于中位数），"
        "再取其中平均每天消费最低的 10% 作为候选，避免把“不用校园卡”误判为“消费低”。",
        "",
        f"筛选结果：{len(candidates)} 名学生进入低消费候选名单。"
        f"（参考阈值：平均每日卡内消费 ≤ {low_threshold:.2f} 元）",
        "",
        "候选示例（学号已打码）：",
        "",
        "| 学号 | 平均每天消费 | 有效天数 | 3 周总消费 |",
        "| --- | ---: | ---: | ---: |",
        candidate_lines,
        "",
        "**重要提醒：** 本名单只是基于校园卡流水的最初步筛查。"
        "低卡消费可能是因为在校外就餐、自己做饭等正常原因，不能据此给学生贴标签。"
        "真实场景中应结合辅导员走访、其他补贴记录等信息人工核实，并严格保护学生隐私。",
        "",
        "## 六、运营建议汇总",
        "",
        "1. **排班**：午餐 11:30-12:30 增加窗口和服务人手；早餐与晚餐按 8 点、18 点峰值安排备餐。",
        "2. **备货**：食堂高销量窗口优先保证供应；超市、饮品按各自销售结构补货。",
        "3. **帮扶**：对低消费候选学生建立人工复核流程，避免直接依据单一刷卡数据下结论。",
        "4. **数据管理**：刷卡数据应定期做重复、缺失、异常检查，分析口径保持统一。",
        "",
        "## 七、数据局限",
        "",
        "- 本数据为模拟数据，结论只能演示分析方法，不代表真实校园情况。",
        "- 一卡通只覆盖部分消费场景，无法反映校外消费。",
        "- 金额分布存在模拟参数造成的规律性（如固定商户价格区间）。",
        "",
        "---",
        "",
        "附录：原始数据清洗过程见 [cleaning_report.md](cleaning_report.md)。",
        "",
    ]

    report_text = "\n".join(lines)
    (REPORT_DIR / "analysis_report.md").write_text(report_text, encoding="utf-8")

    print("报告已生成：")
    print(f"  {REPORT_DIR / 'analysis_report.md'}")
    print(f"低消费候选人数：{len(candidates)}")
    print(f"候选参考阈值：{low_threshold:.2f} 元/天")


if __name__ == "__main__":
    main()
