# 校园一卡通消费分析

一个给大数据管理与应用专业学生练手的数据分析 + AI Agent 项目。

思路：先自己生成一张"模拟的校园一卡通消费流水"，再依次完成
**数据清洗 → 多维度统计 → 可视化 → 结论报告 → AI 问答 Agent**。

当前进度：数据分析全流程 + AI 数据分析 Agent + Web 问答界面已完成

## 项目结构

```text
campus-card-analysis/
├── data/                     # 原始数据与清洗后数据
├── analysis/                 # Python 分析脚本与 AI Agent
├── reports/                  # 图表与报告
├── docs/agent_demo.md        # AI Agent 实测问答记录
├── app.py                    # Streamlit Web 问答界面
├── requirements.txt          # 数据分析基础依赖
├── requirements-agent.txt    # AI Agent 依赖（zai-sdk）
├── requirements-web.txt      # Web 界面依赖（streamlit）
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

数据分析流水线：

```bash
python analysis/clean_data.py            # 数据清洗
python analysis/analyze_consumption.py   # 多维度分析并出图
python analysis/build_report.py          # 生成结论报告
```

产出位于 `data/clean_transactions.csv` 和 `reports/`
（清洗报告 `cleaning_report.md`、分析报告 `analysis_report.md`、图表 PNG）。

## AI 数据分析 Agent

`analysis/data_agent.py` 是一个最小可用的 AI Agent：
大模型（智谱 GLM）负责理解中文问题并决定调用哪些工具，
pandas 函数负责真实执行统计，最后模型基于工具返回的数字作答，
因此回答可追溯、可验证，不会凭空编造。

当前提供 9 个分析工具：数据总览、时段高峰、商户营业额、品类占比、
学院/年级/性别对比、低消费候选筛查，以及单个学生的消费画像。
回答如果涉及已生成的图表，Agent 会自动在末尾附上对应 PNG 的 Markdown 引用。

安装 Agent 依赖并配置智谱 API Key：

```bash
pip install -r requirements-agent.txt
```

配置 `ZHIPU_API_KEY`（也可在命令行里临时设置）后运行：

```bash
python analysis/data_agent.py --question "哪个商户营业额最高？"
python analysis/data_agent.py --trace   # 交互模式，并显示每次工具调用
```

默认模型为 `glm-4.6v`，可用环境变量 `DATA_AGENT_MODEL` 覆盖。

实测问答记录见 [docs/agent_demo.md](docs/agent_demo.md)。

## Web 聊天界面

基于 Streamlit 的网页版问答界面：

```bash
pip install -r requirements-web.txt
streamlit run app.py
```

浏览器会自动打开本地页面；需要先设置 `ZHIPU_API_KEY`。
