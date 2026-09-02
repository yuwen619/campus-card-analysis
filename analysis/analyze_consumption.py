"""第 3 步：对清洗后的数据做多维度分析并画图。

运行方式：
    python analysis/analyze_consumption.py

产出（都在 reports/ 下）：
    hourly_activity.png          各时段消费笔数折线图（消费高峰）
    merchant_revenue.png         各商户营业额对比图
    amount_distribution.png      单笔消费金额分布直方图
    college_per_capita.png       各学院学生人均日消费对比图

数据说明：分析基于 data/clean_transactions.csv（第 2 步清洗结果），
并与 data/student_info.csv 合并以获得学院等信息。
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # 无窗口环境下只保存图片，不弹出窗口

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
REPORT_DIR = ROOT / "reports"

# 中文字体：优先微软雅黑，画图时标题/坐标轴才不乱码
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False


def load_clean() -> pd.DataFrame:
    """读取清洗后的流水，合并学生表，并补充时间相关字段。"""
    transactions = pd.read_csv(
        DATA_DIR / "clean_transactions.csv", dtype={"student_id": "string"}
    )
    students = pd.read_csv(DATA_DIR / "student_info.csv", dtype={"student_id": "string"})

    frame = transactions.merge(students, on="student_id", how="left")
    frame["datetime"] = pd.to_datetime(frame["date"].astype(str) + " " + frame["time"])
    frame["hour"] = frame["datetime"].dt.hour
    return frame


def plot_hourly_activity(frame: pd.DataFrame) -> Path:
    """消费高峰：一天各小时有多少笔消费。"""
    hourly = frame["hour"].value_counts().sort_index()

    plt.figure(figsize=(9, 4.5))
    plt.plot(hourly.index, hourly.values, marker="o", linewidth=2)
    plt.title("各时段消费笔数（3 周汇总）")
    plt.xlabel("小时")
    plt.ylabel("消费笔数")
    plt.xticks(range(0, 24))
    plt.grid(axis="y", linestyle="--", alpha=0.5)
    plt.tight_layout()

    path = REPORT_DIR / "hourly_activity.png"
    plt.savefig(path, dpi=150)
    plt.close()
    return path


def plot_merchant_revenue(frame: pd.DataFrame) -> Path:
    """热门商户：各商户贡献了多少营业额（只看前 10）。"""
    revenue = (
        frame.groupby("merchant", as_index=False)["amount"]
        .sum()
        .sort_values("amount", ascending=True)
        .tail(10)
    )

    plt.figure(figsize=(9, 5))
    plt.barh(revenue["merchant"], revenue["amount"], color="#0EA5E9")
    plt.title("各商户营业额 TOP 10")
    plt.xlabel("营业额（元）")
    plt.ylabel("商户")
    plt.tight_layout()

    path = REPORT_DIR / "merchant_revenue.png"
    plt.savefig(path, dpi=150)
    plt.close()
    return path


def plot_amount_distribution(frame: pd.DataFrame) -> Path:
    """单笔消费金额长什么样（分布是否集中、有没有异常拖尾）。"""
    plt.figure(figsize=(9, 4.5))
    plt.hist(frame["amount"], bins=range(0, 201, 5), color="#10B981", edgecolor="white")
    plt.title("单笔消费金额分布")
    plt.xlabel("金额（元）")
    plt.ylabel("笔数")
    plt.xlim(0, 200)
    plt.grid(axis="y", linestyle="--", alpha=0.5)
    plt.tight_layout()

    path = REPORT_DIR / "amount_distribution.png"
    plt.savefig(path, dpi=150)
    plt.close()
    return path


def plot_college_per_capita(frame: pd.DataFrame, students: pd.DataFrame) -> Path:
    """各学院学生的人均日消费（总额 ÷ 学院人数 ÷ 天数），可比性强。"""
    n_days = frame["date"].nunique()

    college_amount = frame.groupby("college")["amount"].sum()
    college_count = students.groupby("college").size()
    per_capita_daily = (college_amount / (college_count * n_days)).sort_values()

    plt.figure(figsize=(9, 4.5))
    plt.bar(per_capita_daily.index, per_capita_daily.values, color="#F59E0B")
    plt.title(f"各学院学生人均日消费（{n_days} 天）")
    plt.xlabel("学院")
    plt.ylabel("人均日消费（元）")
    plt.xticks(rotation=15)
    plt.tight_layout()

    path = REPORT_DIR / "college_per_capita.png"
    plt.savefig(path, dpi=150)
    plt.close()
    return path


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    frame = load_clean()
    students = pd.read_csv(DATA_DIR / "student_info.csv", dtype={"student_id": "string"})

    # 生成 4 张图
    hourly_path = plot_hourly_activity(frame)
    merchant_path = plot_merchant_revenue(frame)
    amount_path = plot_amount_distribution(frame)
    college_path = plot_college_per_capita(frame, students)

    # 控制台打印一些关键数字，方便和后面的报告对照
    total_revenue = frame["amount"].sum()
    avg_amount = frame["amount"].mean()
    category_revenue = frame.groupby("category")["amount"].sum().sort_values(ascending=False)
    weekday_count = frame["datetime"].dt.dayofweek.map(lambda d: "工作日" if d < 5 else "周末").value_counts()
    top_merchant = (
        frame.groupby("merchant")["amount"].sum().sort_values(ascending=False).index[0]
    )

    print("分析完成，关键数字：")
    print(f"  总营业额：{total_revenue:.2f} 元")
    print(f"  平均单笔消费：{avg_amount:.2f} 元")
    print(f"  营业额最高的商户：{top_merchant}")
    print("  各品类营业额：")
    for category, revenue in category_revenue.items():
        print(f"    {category}：{revenue:.2f} 元")
    print("  工作日/周末消费笔数：")
    for label, count in weekday_count.items():
        print(f"    {label}：{count} 笔")
    print("图表已保存：")
    for path in [hourly_path, merchant_path, amount_path, college_path]:
        print(f"  {path}")


if __name__ == "__main__":
    main()
