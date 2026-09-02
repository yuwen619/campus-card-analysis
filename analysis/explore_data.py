"""第 1 步配套：用 pandas 初探刚生成的原始数据。

运行方式：
    python analysis/explore_data.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"


def main() -> None:
    # 学号是"标识符"不是数字，指定按字符串读取，避免出现 20230041.0
    raw = pd.read_csv(DATA_DIR / "raw_transactions.csv", dtype={"student_id": "string"})
    students = pd.read_csv(DATA_DIR / "student_info.csv", dtype={"student_id": "string"})

    print("=" * 50)
    print("1) 流水表前 10 行：看长什么样")
    print("=" * 50)
    print(raw.head(10))
    print()

    print("=" * 50)
    print("2) 基本信息 info()：看列类型、有没有空值、占多少内存")
    print("=" * 50)
    # 手动复制 info 的写法，便于逐列看
    print("列数：", raw.shape[1], "| 行数：", raw.shape[0])
    for column in raw.columns:
        non_null = raw[column].notna().sum()
        print(f"  {column:<16} 非空 {non_null:>6} / {len(raw)}")
    print()

    print("=" * 50)
    print("3) 数值列 describe()：金额的统计概况")
    print("=" * 50)
    print(raw["amount"].describe())
    print()

    print("=" * 50)
    print("4) 脏数据预检（第 2 步会正式处理）")
    print("=" * 50)
    dup_all = raw.duplicated(subset=raw.columns.drop("transaction_id")).sum()
    missing_sid = (raw["student_id"].isna() | (raw["student_id"].str.strip() == "")).sum()
    zero_amount = (raw["amount"] == 0).sum()
    big_amount = (raw["amount"] > 200).sum()
    print(f"  重复记录（内容相同）：{dup_all}")
    print(f"  空学号：{missing_sid}")
    print(f"  金额为 0：{zero_amount}")
    print(f"  金额大于 200（疑似异常）：{big_amount}")
    print()

    print("=" * 50)
    print("5) 学生表前 5 行")
    print("=" * 50)
    print(students.head())


if __name__ == "__main__":
    main()
