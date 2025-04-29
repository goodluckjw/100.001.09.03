import streamlit as st
import os
import importlib.util

st.set_page_config(layout="wide")

# 스타일 및 크기 조정
st.markdown("""
<style>
    .circle-number {
        display: inline-block;
        border: 1px solid #000;
        border-radius: 50%;
        width: 1.4em;
        height: 1.4em;
        text-align: center;
        line-height: 1.4em;
        font-weight: bold;
        margin-right: 0.4em;
    }
    .small-title {
        font-size: 80%;
    }
    .input-container {
        width: 70%;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="small-title">📘 부칙개정 도우미 (100.001.09)</h1>', unsafe_allow_html=True)

# law_processor import
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app"))
processor_path = os.path.join(base_dir, "law_processor.py")
spec = importlib.util.spec_from_file_location("law_processor", processor_path)
law_processor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(law_processor)

run_search_logic = law_processor.run_search_logic
run_amendment_logic = law_processor.run_amendment_logic

with st.expander("ℹ️ 사용법 안내"):
    st.markdown(
        "- 이 앱은 두 가지 기능을 제공합니다:\n"
        "  1. **검색 기능**: 특정 단어가 포함된 법령 조문을 탐색합니다.\n"
        "  2. **개정문 생성 기능**: 특정 단어를 다른 단어로 바꾸는 부칙 개정문을 자동으로 작성합니다.\n"
        "- 사용 전 `.streamlit/secrets.toml`에 `OC`를 설정해 주세요."
    )

st.header("🔍 검색 기능")
search_query = st.text_input("검색어 입력", key="search_query")
search_unit = st.radio("검색 단위 선택", ["법률", "조", "항", "호", "목"], horizontal=True, index=0)

col1, col2 = st.columns([1, 1])
with col1:
    do_search = st.button("검색 시작")
with col2:
    do_reset = st.button("초기화")

if do_search and search_query:
    with st.spinner("🔍 검색 중..."):
        search_result = run_search_logic(search_query, search_unit)
        st.success(f"{len(search_result)}개의 법률을 찾았습니다")
        for law_name, sections in search_result.items():
            with st.expander(f"📄 {law_name}"):
                for html in sections:
                    st.markdown(html, unsafe_allow_html=True)

if do_reset:
    st.experimental_rerun()

st.header("✏️ 타법개정문 생성")
find_word = st.text_input("찾을 단어", key="find_word")
replace_word = st.text_input("바꿀 단어", key="replace_word")
do_amend = st.button("개정문 생성")

if do_amend and find_word and replace_word:
    with st.spinner("🛠 개정문 생성 중..."):
        amend_result = run_amendment_logic(find_word, replace_word)
        st.success("개정문 생성 완료")
        for amend in amend_result:
            st.markdown(amend, unsafe_allow_html=True)

