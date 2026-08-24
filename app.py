import streamlit as st

st.set_page_config(
    page_title="AI 웹소설 집필 스튜디오",
    page_icon="✍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 세션 상태 안전 초기화
if "novel_text" not in st.session_state:
    st.session_state.novel_text = ""
if "char_profiles" not in st.session_state:
    st.session_state.char_profiles = ""

# 사이드바
with st.sidebar:
    st.header("⚙️ 집필 파라미터")
    api_key = st.text_input("API Key 입력", type="password")
    model_choice = st.selectbox("모델", ["GPT-4o", "Claude 3.5 Sonnet", "Gemini 1.5 Pro"])
    temperature = st.slider("창의성 (Temperature)", 0.0, 1.5, 0.7, 0.1)

# 메인 탭
tab1, tab2 = st.tabs(["등장인물 설정", "소설 본문 집필"])

with tab1:
    st.subheader("2-2. 등장인물 프로필 상세화 및 조연 확장")
    char_req = st.text_area("추가/보완 요청 사항", placeholder="예: 주요 인물 프로필 완성, 조력자 추가", height=80)
    
    col1, col2, col3 = st.columns(3)
    c1 = col1.checkbox("고유 캐릭터 원안 반영", value=False)
    c2 = col2.checkbox("고유 스토리 설정 반영", value=False)
    c3 = col3.checkbox("확장 세계관 반영", value=False)
    
    if st.button("👥 캐릭터 프로필 생성 및 확장", use_container_width=True):
        st.session_state.char_profiles = f"등장인물 프로필 생성 완료\n요청사항: {char_req}"
        st.rerun()

    st.text_area("완성된 등장인물 상세 설정집", value=st.session_state.char_profiles, height=150)

with tab2:
    st.subheader("✍️ 소설 본문")
    
    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
        scene = st.text_input("장면 지시사항", placeholder="예: 비 내리는 재개발 구역 살인 현장")
    with col_t2:
        gen_btn = st.button("🚀 본문 생성 / 확장", use_container_width=True)

    if gen_btn:
        sample_text = (
            "**제1화: 시작**\n\n"
            "장대비가 쏟아지는 서대문구 남가좌동의 낡은 재개발 구역.\n\n"
            "노란색 'KEEP OUT' 경찰 통제선이 거센 빗줄기에 사정없이 흔들렸다. "
            "붉은색과 푸른색 경광등이 젖은 보도블록 위에서 기괴하게 엇갈리며 번뜩였다.\n\n"
            "“아니, 백 형사! 제정신이야? 지금 살인 현장 가시성 보존도 안 됐는데 누구를 데리고 들어오는 거야!”"
        )
        st.session_state.novel_text = sample_text
        st.rerun()

    # 입력값 실시간 동기화 콜백
    def update_editor():
        st.session_state.novel_text = st.session_state["editor_box"]

    st.text_area(
        "작성된 소설 본문 (직접 편집 가능)",
        value=st.session_state.novel_text,
        height=300,
        key="editor_box",
        on_change=update_editor
    )

    # 글자수 계산
    text_val = st.session_state.novel_text
    char_count = len(text_val)
    char_no_space = len(text_val.replace(" ", "").replace("\n", ""))

    m1, m2 = st.columns(2)
    m1.metric("공백 포함 글자수", f"{char_count:,} 자")
    m2.metric("공백 제외 글자수", f"{char_no_space:,} 자")

    # 모바일 복사 방지 해제 뷰어
    with st.expander("📱 스마트폰 독자 뷰어 모드", expanded=True):
        st.markdown(
            f"""
            <div style="user-select: text !important; -webkit-user-select: text !important; background-color: #111; color: #fff; padding: 15px; border-radius: 8px; line-height: 1.8; white-space: pre-wrap;">
            {text_val if text_val else "작성된 본문이 없습니다."}
            </div>
            """,
            unsafe_allow_html=True
        )
