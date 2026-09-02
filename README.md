# 校园一卡通消费分析

一个给大数据管理与应用专业学生练手的数据分析小项目。

思路：先自己生成一张"模拟的校园一卡通消费流水"，再依次完成
**数据清洗 → 多维度统计 → 可视化 → 结论报告**。

当前进度：第 4 步（结论报告）已完成，待第 5 步整理成 GitHub 作品

## 项目结构

```text
campus-card-analysis/
├── data/             # 原始数据与清洗后数据
├── analysis/         # Python 脚本
├── reports/          # 图表与报告（后续步骤生成）
├── requirements.txt  # 依赖清单
└── README.md
```

## 怎么运行（本机需先装 Python 3.11+）

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
python analysis/generate_data.py
python analysis/explore_data.py
```

运行后 `data/` 里会出现两个原始文件：

- `raw_transactions.csv`：一卡通消费流水（含故意埋入的脏数据）
- `student_info.csv`：学生基本信息

后续步骤依次运行：

```bash
python analysis/clean_data.py            # 第 2 步：清洗
python analysis/analyze_consumption.py   # 第 3 步：分析并出图
python analysis/build_report.py          # 第 4 步：生成结论报告
```

清洗、分析与报告产出分别位于 `data/clean_transactions.csv` 和 `reports/`
（清洗报告 `cleaning_report.md`、分析报告 `analysis_report.md`、图表 PNG）。
