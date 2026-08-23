import streamlit as st
import json
import streamlit.components.v1 as components
from google import genai

st.set_page_config(page_title="웹소설 스튜디오", layout="wide")

# 1. API 키 자동 유지 (Secrets 1순위 -> 사이드바 수동 입력 2순위)
api_key = st.secrets.get("GEMINI_API_KEY", "")

with st.sidebar:
    st.header("⚙️ 설정 및 백업")
    user_key = st.text_input("Gemini API Key", value=api_key, type="password", help="Secrets에 저장되어 있으면 자동 적용됩니다.")
    if user_key:
        api_key = user_key

# 2. 세션 상태 초기화
if "synopsis" not in st.session_state:
    st.session_state.synopsis = ""
if "characters" not in st.session_state:
    st.session_state.characters = ""
if "episodes" not in st.session_state:
    st.session_state.episodes = ""

# 3. 사이드바: 파일 백업 & 복원
with st.sidebar:
    st.markdown("---")
    st.subheader("💾 파일 백업 & 복원")
    
    uploaded_file = st.file_uploader("백업 파일 불러오기 (.json)", type=["json"])
    if uploaded_file is not None:
        try:
            data = json.load(uploaded_file)
            st.session_state.synopsis = data.get("synopsis", "")
            st.session_state.characters = data.get("characters", "")
            st.session_state.episodes = data.get("episodes", "")
            st.success("백업 데이터를 성공적으로 불러왔습니다!")
        except Exception as e:
            st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")

    current_project = {
        "synopsis": st.session_state.synopsis,
        "characters": st.session_state.characters,
        "episodes": st.session_state.episodes
    }
    project_json = json.dumps(current_project, ensure_ascii=False, indent=2)
    st.download_button(
        label="📥 현재 작업 파일 백업 (JSON)",
        data=project_json,
        file_name="webnovel_backup.json",
        mime="application/json"
    )

    if st.button("🗑️ 브라우저 자동 저장 비우기"):
        components.html(
            """
            <script>
                localStorage.removeItem('novel_studio_backup');
                window.parent.location.reload();
            </script>
            """,
            height=0
        )

# 4. 브라우저 실시간 자동 저장
save_payload = json.dumps({
    "synopsis": st.session_state.synopsis,
    "characters": st.session_state.characters,
    "episodes": st.session_state.episodes
})

components.html(
    f"""
    <script>
        const currentData = {save_payload};
        if (currentData.synopsis || currentData.characters || currentData.episodes) {{
            localStorage.setItem('novel_studio_backup', JSON.stringify(currentData));
        }}
    </script>
    """,
    height=0
)

# 5. 메인 화면 구성
st.title("✍️ 웹소설 유니버스 & 멀티 채널 스튜디오")

if not api_key:
    st.warning("👈 사이드바에 Gemini API Key를 입력하거나 Secrets 설정을 완료해 주세요.")
    st.stop()

client = genai.Client(api_key=api_key)
MODEL_NAME = "gemini-3.6-flash"

tab1, tab2, tab3 = st.tabs(["🎲 시놉시스 & 기획", "👥 캐릭터 설정", "📖 본문 집필"])

# 탭 1: 시놉시스
with tab1:
    st.subheader("시놉시스 기획")
    genre = st.selectbox("장르 선택", ["판타지", "무협", "로맨스판타지", "현대판타지", "미스터리/추리", "SF"])
    prompt_input = st.text_area("핵심 키워드 또는 아이디어", placeholder="예: 실종 수사관과 사건 추적")

    if st.button("🎲 시놉시스 주사위 굴리기 (생성)"):
        with st.spinner("AI가 시놉시스를 생성 중입니다..."):
            try:
                response = client.models.generate_content(
                    model=MODEL_NAME,
                    contents=f"장르: {genre}\n키워드: {prompt_input}\n흥미진진한 웹소설 시놉시스와 메인 플롯을 작성해줘."
                )
                st.session_state.synopsis = response.text
                st.rerun()
            except Exception as e:
                st.error(f"생성 중 오류 발생: {e}")

    st.session_state.synopsis = st.text_area("작성/수정된 시놉시스", value=st.session_state.synopsis, height=250)

# 탭 2: 캐릭터
with tab2:
    st.subheader("등장인물 설계")
    char_prompt = st.text_input("캐릭터 컨셉 요약", placeholder="예: 냉철한 형사, 비밀을 간직한 추적자")
    
    if st.button("👥 캐릭터 자동 생성"):
        with st.spinner("캐릭터 프로필을 생성 중입니다..."):
            try:
                response = client.models.generate_content(
                    model=MODEL_NAME,
                    contents=f"시놉시스: {st.session_state.synopsis}\n요청: {char_prompt}\n주요 인물 성격, 외모, 갈등 요소를 자세히 작성해줘."
                )
                st.session_state.characters = response.text
                st.rerun()
            except Exception as e:
                st.error(f"생성 중 오류 발생: {e}")

    st.session_state.characters = st.text_area("등장인물 설정집", value=st.session_state.characters, height=250)

# 탭 3: 본문
with tab3:
    st.subheader("에피소드 / 본문 집필")
    episode_goal = st.text_input("이번 화 목표/사건", placeholder="예: 1화 - 첫 번째 단서 발견")
    
    if st.button("📖 본문 초안 작성"):
        with st.spinner("웹소설 본문을 집필 중입니다..."):
            try:
                response = client.models.generate_content(
                    model=MODEL_NAME,
                    contents=f"시놉시스: {st.session_state.synopsis}\n등장인물: {st.session_state.characters}\n이번 화: {episode_goal}\n웹소설 1화 분량의 본문 초안을 작성해줘."
                )
                st.session_state.episodes = response.text
                st.rerun()
            except Exception as e:
                st.error(f"본문 생성 중 오류 발생: {e}")

    st.session_state.episodes = st.text_area("작성된 소설 본문", value=st.session_state.episodes, height=350)
