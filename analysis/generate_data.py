"""第 1 步：生成校园一卡通模拟数据（含故意埋入的脏数据）。

运行方式：
    python analysis/generate_data.py

产出：
    data/raw_transactions.csv   一卡通消费流水
    data/student_info.csv       学生基本信息
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import random

import pandas as pd


# 项目根目录（analysis 的上一级）
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

# 固定随机种子：每次生成的模拟数据一致，方便复现
random.seed(20260301)

# ---------------- 参数设置 ----------------

N_STUDENTS = 120          # 模拟学生人数
DAYS = 21                  # 模拟天数（3 周）
START_DATE = date(2026, 3, 2)

# 商户：名称 / 大类 / 单笔金额范围（元）
MERCHANTS = [
    ("一食堂-大众窗口", "食堂", 8, 15),
    ("一食堂-风味窗口", "食堂", 12, 22),
    ("二食堂-大众窗口", "食堂", 8, 15),
    ("二食堂-面食窗口", "食堂", 10, 18),
    ("超市A",            "超市", 2, 15),
    ("便利店",            "超市", 3, 20),
    ("水果店",            "超市", 4, 30),
    ("奶茶店",            "饮品", 6, 18),
    ("咖啡店",            "饮品", 8, 25),
]

COLLEGES = ["信息管理学院", "经济学院", "计算机学院", "外国语学院", "理学院"]
GRADES = [2022, 2023, 2024, 2025]


# ---------------- 生成学生信息 ----------------

def make_students() -> pd.DataFrame:
    records = []
    for i in range(1, N_STUDENTS + 1):
        # 学号 = 入学年份 + 4 位序号，例如 20240001
        grade = GRADES[i % len(GRADES)]
        student_id = int(f"{grade}{i:04d}")
        records.append(
            {
                "student_id": student_id,
                "grade": grade,
                "college": random.choice(COLLEGES),
                "gender": random.choice(["男", "女"]),
            }
        )
    return pd.DataFrame(records)


# ---------------- 生成消费流水 ----------------

def make_transactions(students: pd.DataFrame) -> list[dict]:
    """按真实生活规律模拟消费：三餐有固定高峰，周末早餐概率更低。"""

    student_ids = students["student_id"].tolist()
    rows: list[dict] = []

    for day_offset in range(DAYS):
        current_date = START_DATE + timedelta(days=day_offset)
        is_weekend = current_date.weekday() >= 5

        for sid in student_ids:
            # 早餐：工作日大部分人去，周末很多人睡懒觉
            if random.random() < (0.25 if is_weekend else 0.75):
                rows.append(meal_row(sid, current_date, "breakfast"))

            # 午餐、晚餐：基本稳定
            if random.random() < 0.92:
                rows.append(meal_row(sid, current_date, "lunch"))
            if random.random() < 0.88:
                rows.append(meal_row(sid, current_date, "dinner"))

            # 偶尔去超市 / 奶茶店加餐
            if random.random() < 0.20:
                rows.append(store_row(sid, current_date))

    # 注入脏数据：重复记录、空学号、0 金额、异常大金额
    inject_dirt(rows)
    random.shuffle(rows)

    frame = pd.DataFrame(rows)
    frame.insert(0, "transaction_id", [f"T{i:07d}" for i in range(1, len(frame) + 1)])
    return frame


def meal_row(student_id: int, current_date: date, meal: str) -> dict:
    """一顿饭：从食堂里随机选窗口，金额落在对应区间。"""
    canteens = [m for m in MERCHANTS if m[1] == "食堂"]
    name, category, low, high = random.choice(canteens)
    hour_weights = {
        "breakfast": [(7, 0.45), (8, 0.55)],
        "lunch":     [(11, 0.25), (12, 0.55), (13, 0.20)],
        "dinner":    [(17, 0.40), (18, 0.60)],
    }
    hour, minute = pick_time(hour_weights[meal])
    return {
        "student_id": student_id,
        "date": current_date.isoformat(),
        "time": f"{hour:02d}:{minute:02d}:00",
        "merchant": name,
        "category": category,
        "amount": round(random.uniform(low, high), 2),
    }


def store_row(student_id: int, current_date: date) -> dict:
    """一次加餐：从超市 / 饮品里随机选一个商户。"""
    stores = [m for m in MERCHANTS if m[1] != "食堂"]
    name, category, low, high = random.choice(stores)
    hour, minute = pick_time([(10, 0.20), (15, 0.30), (19, 0.30), (21, 0.20)])
    return {
        "student_id": student_id,
        "date": current_date.isoformat(),
        "time": f"{hour:02d}:{minute:02d}:00",
        "merchant": name,
        "category": category,
        "amount": round(random.uniform(low, high), 2),
    }


def pick_time(weighted_hours: list[tuple[int, float]]) -> tuple[int, int]:
    """按概率选小时，再随机分钟。用来制造午餐 12 点这样的高峰。"""
    hours = [h for h, _ in weighted_hours]
    weights = [w for _, w in weighted_hours]
    hour = random.choices(hours, weights=weights, k=1)[0]
    minute = random.randint(0, 59)
    return hour, minute


def inject_dirt(rows: list[dict]) -> None:
    """故意制造脏数据，供第 2 步清洗练习。"""

    # 1) 约 0.6% 的重复记录（内容完全一样）
    n_dup = max(1, int(len(rows) * 0.006))
    for sample in random.sample(rows, n_dup):
        rows.append(dict(sample))

    # 2) 空学号：模拟刷卡记录没关联到人
    for index in random.sample(range(len(rows)), 8):
        rows[index]["student_id"] = ""

    # 3) 金额为 0：模拟机器误刷
    for index in random.sample(range(len(rows)), 6):
        rows[index]["amount"] = 0.0

    # 4) 异常大金额：模拟错误录入或重复扣款
    for index in random.sample(range(len(rows)), 5):
        rows[index]["amount"] = round(random.uniform(300, 1500), 2)


# ---------------- 主流程 ----------------

def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    students = make_students()
    transactions = make_transactions(students)

    # 用 utf-8-sig 编码，Excel 打开中文不会乱码
    transactions.to_csv(DATA_DIR / "raw_transactions.csv", index=False, encoding="utf-8-sig")
    students.to_csv(DATA_DIR / "student_info.csv", index=False, encoding="utf-8-sig")

    print(f"学生数：{len(students)}")
    print(f"流水行数：{len(transactions)}")
    print(f"日期范围：{transactions['date'].min()} ~ {transactions['date'].max()}")
    print("文件已写入：")
    print(f"  {DATA_DIR / 'raw_transactions.csv'}")
    print(f"  {DATA_DIR / 'student_info.csv'}")


if __name__ == "__main__":
    main()
