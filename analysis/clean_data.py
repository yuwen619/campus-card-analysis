"""第 2 步：清洗校园一卡通消费数据。

运行方式：
    python analysis/clean_data.py

产出：
    data/clean_transactions.csv   清洗后的流水表
    reports/cleaning_report.md    清洗过程报告

清洗原则：每一步都要能说清楚"删了什么、为什么删"，
所以本脚本把每条规则当成独立一步，并记录前后行数。
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
REPORT_DIR = ROOT / "reports"

# 超出该金额认为异常（校园一卡通单笔消费超过 200 元不合理）
AMOUNT_UPPER = 200


def load_raw() -> tuple[pd.DataFrame, pd.DataFrame]:
    """读取原始数据。学号按字符串读，避免出现 20230041.0。"""
    raw = pd.read_csv(DATA_DIR / "raw_transactions.csv", dtype={"student_id": "string"})
    students = pd.read_csv(DATA_DIR / "student_info.csv", dtype={"student_id": "string"})
    return raw, students


def drop_rows(frame: pd.DataFrame, mask: pd.Series, note: str, steps: list[dict]) -> pd.DataFrame:
    """按保留条件 mask 过滤，并把这一步记进清洗日志。"""
    before = len(frame)
    cleaned = frame[mask].copy()
    steps.append(
        {
            "note": note,
            "removed": before - len(cleaned),
            "before": before,
            "after": len(cleaned),
        }
    )
    return cleaned


def make_markdown_table(steps: list[dict]) -> str:
    lines = [
        "| 清洗步骤 | 处理前行数 | 删除行数 | 处理后行数 | 说明 |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for step in steps:
        lines.append(
            f"| {step['note']} | {step['before']} | {step['removed']} | "
            f"{step['after']} | 见上文规则说明 |"
        )
    return "\n".join(lines)


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    raw, students = load_raw()
    valid_ids = set(students["student_id"].dropna().astype(str))
    steps: list[dict] = []

    # 内容列：判断重复时不能用 transaction_id，因为它是流水编号，
    # 同一次刷卡被重复录入时会得到两个不同编号。
    content_cols = [c for c in raw.columns if c != "transaction_id"]

    # ---- 规则 1：删除内容完全相同的重复记录 ----
    dup_mask = raw.duplicated(subset=content_cols, keep="first")
    frame = drop_rows(raw, ~dup_mask, "删除重复记录", steps)

    # ---- 规则 2：删除空学号（无法关联到学生，后续分析用不上）----
    has_id = frame["student_id"].notna() & (frame["student_id"].fillna("").astype(str).str.strip() != "")
    frame = drop_rows(frame, has_id, "删除空学号记录", steps)

    # ---- 规则 3：删除学生信息表里不存在的学号（孤儿数据）----
    known_id = frame["student_id"].astype(str).isin(valid_ids)
    frame = drop_rows(frame, known_id, "删除未知学号记录", steps)

    # ---- 规则 4：删除金额 <= 0 的记录（0 元误刷 / 负数退款等）----
    positive_amount = frame["amount"] > 0
    frame = drop_rows(frame, positive_amount, "删除金额非正的记录", steps)

    # ---- 规则 5：删除金额过大的异常记录（> 200 元）----
    reasonable_amount = frame["amount"] <= AMOUNT_UPPER
    frame = drop_rows(frame, reasonable_amount, "删除异常大金额记录", steps)

    # ---- 规则 6：删除关键字段缺失的记录（日期/时间/商户/类别）----
    has_key_fields = (
        frame["date"].notna()
        & frame["time"].notna()
        & frame["merchant"].notna()
        & frame["category"].notna()
    )
    frame = drop_rows(frame, has_key_fields, "删除关键字段缺失记录", steps)

    # 重置索引，让行号从 0 连续
    clean = frame.reset_index(drop=True)

    # 保存清洗结果
    clean.to_csv(DATA_DIR / "clean_transactions.csv", index=False, encoding="utf-8-sig")

    # ---- 校验清洗结果 ----
    checks = [
        ("重复记录数", clean.duplicated(subset=content_cols).sum()),
        ("空学号数", clean["student_id"].isna().sum()),
        ("未知学号数", (~clean["student_id"].astype(str).isin(valid_ids)).sum()),
        ("非正金额数", (clean["amount"] <= 0).sum()),
        ("异常大金额数", (clean["amount"] > AMOUNT_UPPER).sum()),
    ]

    # ---- 生成清洗报告 ----
    report_lines = [
        "# 数据清洗报告",
        "",
        f"- 数据来源：`data/raw_transactions.csv`",
        f"- 原始行数：{len(raw)}",
        f"- 清洗后行数：{len(clean)}",
        f"- 共删除：{len(raw) - len(clean)} 行",
        "",
        "## 清洗规则说明",
        "",
        "1. **删除重复记录**：同一次刷卡被重复录入，内容完全相同的记录只保留一条。",
        "2. **删除空学号记录**：无法关联到具体学生，无法做个人维度的分析。",
        "3. **删除未知学号记录**：学号不在学生信息表中，属于无主数据。",
        "4. **删除金额非正记录**：金额 0 通常是机器误刷，负数是退款，都不能当正常消费。",
        "5. **删除异常大金额记录**：单笔超过 200 元与校园消费场景不符，疑似错误录入。",
        "6. **删除关键字段缺失记录**：日期、时间、商户、类别缺失的记录不可用。",
        "",
        "## 清洗过程记录",
        "",
        make_markdown_table(steps),
        "",
        "## 清洗后校验",
        "",
    ]
    report_lines.extend(f"- {name}：{value}" for name, value in checks)
    report_lines += [
        "",
        "## 结论",
        "",
        f"原始数据 {len(raw)} 行，经清洗后剩 {len(clean)} 行，"
        f"删除 {len(raw) - len(clean)} 行，"
        f"占原始数据的 {(len(raw) - len(clean)) / len(raw):.2%}。"
        "剩余数据可用于后续按学生、时段、商户等维度的分析。",
        "",
    ]
    (REPORT_DIR / "cleaning_report.md").write_text("\n".join(report_lines), encoding="utf-8")

    # 控制台简要输出
    print("清洗完成：")
    print(f"  原始行数：{len(raw)}")
    print(f"  清洗后行数：{len(clean)}")
    print(f"  删除行数：{len(raw) - len(clean)}")
    print("校验结果：")
    for name, value in checks:
        print(f"  {name}：{value}")
    print(f"输出文件：{DATA_DIR / 'clean_transactions.csv'}")
    print(f"清洗报告：{REPORT_DIR / 'cleaning_report.md'}")


if __name__ == "__main__":
    main()
