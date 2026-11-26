import sys
import time
from pathlib import Path

# Make "src" importable when running: streamlit run app/app.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402

from src import llm  # noqa: E402
from src.answer import answer_question  # noqa: E402
from src.search import Searcher  # noqa: E402

MAX_QUESTIONS_PER_SESSION = 15
EXAMPLES = [
    "What was Apple's cost of sales for Services in fiscal 2025?",
    "How did Apple's research and development expense change from fiscal 2024 to fiscal 2025?",
    "What one-time income tax charge did Apple record in fiscal 2024 related to the State Aid Decision?",
    "What were Apple's total net sales in fiscal 2019?",
]

st.set_page_config(page_title="10-K Q&A", page_icon="📄")


@st.cache_resource(show_spinner="Loading the search index...")
def get_searcher():
    return Searcher()


def use_example(text):
    st.session_state.question = text


if "count" not in st.session_state:
    st.session_state.count = 0
if "question" not in st.session_state:
    st.session_state.question = ""

st.title("Ask Apple's 10-K filings")
st.caption(
    "Annual reports for fiscal 2023, 2024 and 2025. Every answer cites the passages "
    "it used, and the system says NOT_FOUND when the filings do not contain the answer."
)

st.write("Try an example:")
for i, example in enumerate(EXAMPLES):
    st.button(example, key=f"ex{i}", on_click=use_example, args=(example,))

question = st.text_input("Your question", key="question")
ask = st.button("Ask", type="primary")

if ask and question.strip():
    if st.session_state.count >= MAX_QUESTIONS_PER_SESSION:
        st.warning("You have reached the question limit for this session.")
        st.stop()
    st.session_state.count += 1
    searcher = get_searcher()
    started = time.time()
    with st.spinner("Searching the filings and writing an answer..."):
        try:
            result = answer_question(searcher, question.strip())
        except Exception as exc:
            st.error(
                "The language model is busy or unavailable right now "
                f"({type(exc).__name__}). Please try again in a minute."
            )
            st.stop()
    elapsed = time.time() - started

    if result["refused"]:
        st.warning("Not found. The filings in this index do not answer that question.")
    else:
        st.markdown(result["answer"])
    year = result["year_filter"]
    st.caption(
        f"Filing filter: {'fiscal ' + str(year) if year else 'none'} | "
        f"model: {llm.LAST_MODEL} | {elapsed:.0f}s"
    )

    st.subheader("Sources")
    by_id = {c["id"]: c for c in searcher.chunks}
    for n, cid in enumerate(result["retrieved"], start=1):
        chunk = by_id[cid]
        cited = cid in result["cited"]
        label = f"[{n}] {chunk['header']}" + ("  (cited)" if cited else "")
        with st.expander(label, expanded=cited):
            st.text(chunk["text"])