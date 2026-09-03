"""校园一卡通 AI 数据分析 Agent 的 Web 聊天界面（Streamlit）。

运行方式（先配置 ZHIPU_API_KEY）：
    pip install -r requirements-web.txt
    streamlit run app.py
"""

from __future__ import annotations

import os
import re

import streamlit as st

from analysis.data_agent import MODEL, ROOT, ask, make_client


st.set_page_config(page_title="校园一卡通 AI 数据分析", page_icon="🎓", layout="centered")

st.title("🎓 校园一卡通 AI 数据分析助手")
st.caption("中文提问 → Agent 规划工具调用 → pandas 真实计算 → 带图表回答")

# 侧边栏：说明与状态
with st.sidebar:
    st.header("使用说明")
    st.markdown(
        "- 数字全部来自工具对清洗后数据的真实计算，不凭空编造\n"
        "- Agent 最多连续调用多轮工具\n"
        "- 涉及低消费名单时会提示需要人工复核\n"
        "- 模型：`" + MODEL + "`"
    )
    api_key_set = bool(os.environ.get("ZHIPU_API_KEY", "").strip())
    if api_key_set:
        st.success("ZHIPU_API_KEY 已配置")
    else:
        st.error("未检测到 ZHIPU_API_KEY，请先设置环境变量")

if not api_key_set:
    st.stop()

client = make_client()

EXAMPLE_QUESTIONS = [
    "哪个商户营业额最高？",
    "哪个小时消费笔数最多？",
    "哪个学院的人均日消费最低？",
    "2022 级和 2024 级学生的人均日消费哪个高？",
    "帮我看看学号 20230001 的消费画像",
    "低消费候选学生有多少人？",
]

if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_question" not in st.session_state:
    st.session_state.pending_question = None


def extract_charts(markdown_text: str) -> tuple[str, list[str]]:
    """把回答里的 ![](reports/x.png) 提取出来，交给 st.image 显示。"""
    charts: list[str] = []

    def replace(match: re.Match[str]) -> str:
        rel_path = match.group(1)
        abs_path = ROOT / rel_path
        if abs_path.exists():
            charts.append(str(abs_path))
        return ""

    text = re.sub(r"!\[[^\]]*\]\(([^)]+)\)", replace, markdown_text)
    return text.strip(), charts


def run_question(question: str) -> None:
    st.session_state.messages.append({"role": "user", "text": question})
    try:
        with st.spinner("Agent 正在分析数据…"):
            raw_answer = ask(client, question, show_trace=True)
        text, charts = extract_charts(raw_answer)
        st.session_state.messages.append({"role": "assistant", "text": text, "charts": charts})
    except Exception as exc:  # 网页里把错误显示给用户，而不是静默失败
        st.session_state.messages.append(
            {
                "role": "assistant",
                "text": f"出错了：{exc}",
                "charts": [],
            }
        )


# 示例问题按钮
st.markdown("**试试这些问题：**")
cols = st.columns(2)
for index, question in enumerate(EXAMPLE_QUESTIONS):
    if cols[index % 2].button(question, key=f"example_{index}", use_container_width=True):
        st.session_state.pending_question = question

prompt = st.chat_input("输入你的问题，例如：哪个食堂最受欢迎？")

if prompt is None and st.session_state.pending_question:
    prompt = st.session_state.pending_question
    st.session_state.pending_question = None

if prompt:
    run_question(prompt)

# 渲染完整聊天记录
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["text"])
        for chart_path in message.get("charts", []):
            st.image(chart_path)
