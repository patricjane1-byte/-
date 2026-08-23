import streamlit as st
import json
import streamlit.components.v1 as components
from google import genai
from google.genai import types

st.set_page_config(page_title="웹소설 스튜디오", layout="wide")

# 1. API 키 자동 유지 (Secrets 1순위 -> 사이드바 수동 입력 2순위)
api_key = st.secrets.get("GEMINI_API_KEY", "")

with st.sidebar:
    st.header("⚙️ 시스템 & AI 제어")
    user_key = st.text_input("Gemini API Key", value=api_key, type="password", help="Secrets에 등록되어 있으면 자동 적용됩니다.")
    if user_key:
        api_key = user_key

    st.markdown("---")
    st.subheader("🎛️ AI 접근 및 표현 수준 설정")
    
    # AI 자유도 및 창의성 (Temperature)
    creativity = st.slider("AI 창의성 / 자유도 (Temperature)", min_value=0.0, max_value=2.0, value=1.0, step=0.1, 
                           help="낮을수록 논리적/정형적, 높을수록 기발하고 파격적인 전개")
    
    # 표현 수위 / 연령 등급
    rating_level = st.selectbox(
        "표현 수위 / 연령 등급",
        ["전체이용가 (대중적/순화)", "15세 이용가 (긴장감/현실적 묘사)", "19세 성인/하드보일드 (적나라한 심리/폭력/어두운 묘사 허용)", "노필터 다크 판타지/스릴러"]
    )
    
    # 묘사 및 문체 디테일 수준
    detail_style = st.selectbox(
        "문체 및 묘사 디테일",
        ["속도감 중심 (대화/사건 위주)", "균형 잡힌 웹소설 표준", "극적 심리/감각적 고밀도 묘사", "클리프행어/도파민 극대화"]
    )
    
    # 생성 목표 분량
    target_length = st.select_slider(
        "생성 분량 목표",
        options=["간략 요약 (~1,000자)", "단편/기본 (~2,500자)", "웹소설 1화 표준 (~4,500자)", "초장문 고밀도 (~6,000자 이상)"],
        value="웹소설 1화 표준 (~4,500자)"
    )

# 2. 세션 상태 (작업 데이터) 초기화
fields = ["worldview", "synopsis", "characters", "plot", "episodes", "notes"]
for f in fields:
    if f not in st.session_state:
        st.session_state[f] = ""

# 3. 사이드바 백업 / 복원
with st.sidebar:
    st.markdown("---")
    st.subheader("💾 데이터 백업 & 복원")
    
    uploaded_file = st.file_uploader("작업 백업 파일 (.json) 불러오기", type=["json"])
    if uploaded_file is not None:
        try:
            data = json.load(uploaded_file)
            for f in fields:
                st.session_state[f] = data.get(f, "")
            st.success("작업 데이터를 성공적으로 불러왔습니다!")
        except Exception as e:
            st.error(f"파일 불러오기 오류: {e}")

    current_project = {f: st.session_state[f] for f in fields}
    project_json = json.dumps(current_project, ensure_ascii=False, indent=2)
    st.download_button(
        label="📥 현재 전체 프로젝트 백업 (JSON)",
        data=project_json,
        file_name="webnovel_universe_backup.json",
        mime="application/json"
    )

    if st.button("🗑️ 브라우저 자동 저장 데이터 비우기"):
        components.html(
            """
            <script>
                localStorage.removeItem('novel_studio_backup_full');
                window.parent.location.reload();
            </script>
            """,
            height=0
        )

# 4. 실시간 브라우저 자동 저장
save_payload = json.dumps(current_project)
components.html(
    f"""
    <script>
        const currentData = {save_payload};
        const hasData = Object.values(currentData).some(v => v !== "");
        if (hasData) {{
            localStorage.setItem('novel_studio_backup_full', JSON.stringify(currentData));
        }}
    </script>
    """,
    height=0
)

# 5. 메인 화면
st.title("✍️ 웹소설 유니버스 & 멀티 채널 스튜디오")

if not api_key:
    st.warning("👈 사이드바에 Gemini API Key를 입력하거나 Secrets 설정을 완료해 주세요.")
    st.stop()

client = genai.Client(api_key=api_key)
MODEL_NAME = "gemini-3.6-flash"

# 프롬프트에 들어갈 공통 지침 텍스트
system_prompt_addon = f"""
[집필 및 제어 가이드라인]
- 표현 수위: {rating_level}
- 문체 스타일: {detail_style}
- 목표 분량: {target_length}
- 독자의 몰입감을 극대화하고 진부한 클리셰를 피할 것.
"""

def generate_ai(contents_text):
    config = types.GenerateContentConfig(
        temperature=creativity,
        system_instruction=system_prompt_addon
    )
    res = client.models.generate_content(
        model=MODEL_NAME,
        contents=contents_text,
        config=config
    )
    return res.text

# 탭 구성
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🌍 세계관 & 기획", 
    "🎲 시놉시스", 
    "👥 등장인물 설정", 
    "🗺️ 플롯 & 트리트먼트", 
    "📖 본문 집필 & 메모"
])

# 탭 1: 세계관
with tab1:
    st.subheader("🌍 세계관 및 기본 셋팅")
    col1, col2 = st.columns(2)
    with col1:
        genre = st.selectbox("장르", ["판타지", "현대판타지", "무협", "로맨스판타지", "SF", "미스터리/스릴러", "다크판타지", "기타"])
        tone = st.text_input("분위기/톤앤매너", placeholder="예: 어둡고 냉철한 하드보일드, 긴박한 추격전")
    with col2:
        concept = st.text_area("핵심 테마 및 소재", placeholder="예: 실종 수사관, 숨겨진 미제 사건, 특수 능력의 이면")

    if st.button("🌍 세계관 및 세력/규칙 자동 생성"):
        with st.spinner("설정 수준에 맞춰 세계관을 구축 중입니다..."):
            try:
                p = f"장르: {genre}\n톤앤매너: {tone}\n핵심 테마: {concept}\n위 내용을 바탕으로 웹소설의 구체적인 세계관, 사회 구조, 세력도, 고유 규칙을 체계적으로 작성해줘."
                st.session_state.worldview = generate_ai(p)
                st.rerun()
            except Exception as e:
                st.error(f"오류: {e}")

    st.session_state.worldview = st.text_area("세계관 설정집", value=st.session_state.worldview, height=300)

# 탭 2: 시놉시스
with tab2:
    st.subheader("🎲 시놉시스 생성")
    synop_keyword = st.text_input("시놉시스 추가 키워드", placeholder="예: 첫 번째 살인 사건, 의문의 단서 발견")

    if st.button("🎲 시놉시스 주사위 굴리기"):
        with st.spinner("시놉시스 생성 중..."):
            try:
                p = f"세계관:\n{st.session_state.worldview}\n추가 키워드: {synop_keyword}\n위 세계관을 바탕으로 몰입도 높은 전체 시놉시스와 메인 갈등 구조를 작성해줘."
                st.session_state.synopsis = generate_ai(p)
                st.rerun()
            except Exception as e:
                st.error(f"오류: {e}")

    st.session_state.synopsis = st.text_area("메인 시놉시스", value=st.session_state.synopsis, height=300)

# 탭 3: 캐릭터
with tab3:
    st.subheader("👥 등장인물 설정집")
    char_desc = st.text_input("추가할 인물 컨셉", placeholder="예: 주인공(이육사), 남성 추적자(추수국), 메인 빌런(황대수)")

    if st.button("👥 캐릭터 프로필 생성"):
        with st.spinner("등장인물 설계 중..."):
            try:
                p = f"세계관:\n{st.session_state.worldview}\n시놉시스:\n{st.session_state.synopsis}\n요청 인물: {char_desc}\n주요 인물들의 이름, 나이, 외모, 성격, 고유 능력, 비밀, 인물 관계도를 상세히 작성해줘."
                st.session_state.characters = generate_ai(p)
                st.rerun()
            except Exception as e:
                st.error(f"오류: {e}")

    st.session_state.characters = st.text_area("등장인물 상세 설정", value=st.session_state.characters, height=300)

# 탭 4: 플롯
with tab4:
    st.subheader("🗺️ 전체 플롯 & 트리트먼트")
    plot_goal = st.text_input("플롯 전개 방향", placeholder="예: 1~10화 도입부 및 첫 번째 위기")

    if st.button("🗺️ 회차별 플롯 설계"):
        with st.spinner("플롯 구성 중..."):
            try:
                p = f"세계관:\n{st.session_state.worldview}\n시놉시스:\n{st.session_state.synopsis}\n등장인물:\n{st.session_state.characters}\n전개 방향: {plot_goal}\n각 화별 기승전결 플롯과 엔딩 클리프행어를 구체적으로 작성해줘."
                st.session_state.plot = generate_ai(p)
                st.rerun()
            except Exception as e:
                st.error(f"오류: {e}")

    st.session_state.plot = st.text_area("회차별 플롯/트리트먼트", value=st.session_state.plot, height=300)

# 탭 5: 본문 및 집필
with tab5:
    st.subheader("📖 에피소드 집필 & 작가 메모")
    ep_num = st.text_input("회차 및 목표", placeholder="예: 제1화 - 빗속의 단서 추적")

    if st.button("📖 본문 초안 작성"):
        with st.spinner("웹소설 본문 집필 중..."):
            try:
                p = f"세계관:\n{st.session_state.worldview}\n등장인물:\n{st.session_state.characters}\n플롯:\n{st.session_state.plot}\n이번 회차: {ep_num}\n설정된 수위와 문체에 맞춰 고품질 웹소설 본문을 작성해줘."
                st.session_state.episodes = generate_ai(p)
                st.rerun()
            except Exception as e:
                st.error(f"오류: {e}")

    st.session_state.episodes = st.text_area("작성된 소설 본문", value=st.session_state.episodes, height=350)
    st.session_state.notes = st.text_area("💡 작가 메모 / 떡밥 수첩", value=st.session_state.notes, height=150)
