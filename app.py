import streamlit as st
import json
import streamlit.components.v1 as components
from google import genai
from google.genai import types

st.set_page_config(page_title="웹소설 스튜디오", layout="wide")

# 1. API 키 자동 유지
api_key = st.secrets.get("GEMINI_API_KEY", "")

with st.sidebar:
    st.header("⚙️ 시스템 & AI 제어")
    user_key = st.text_input("Gemini API Key", value=api_key, type="password", help="Secrets에 등록되어 있으면 자동 적용됩니다.")
    if user_key:
        api_key = user_key

    st.markdown("---")
    st.subheader("🎛️ AI 접근 및 표현 수준 설정")
    
    creativity = st.slider("AI 창의성 / 자유도 (Temperature)", min_value=0.0, max_value=2.0, value=1.0, step=0.1)
    rating_level = st.selectbox(
        "표현 수위 / 연령 등급",
        ["전체이용가 (대중적/순화)", "15세 이용가 (긴장감/현실적 묘사)", "19세 성인/하드보일드 (적나라한 심리/폭력/어두운 묘사 허용)", "노필터 다크 판타지/스릴러"]
    )
    detail_style = st.selectbox(
        "문체 및 묘사 디테일",
        ["속도감 중심 (대화/사건 위주)", "균형 잡힌 웹소설 표준", "극적 심리/감각적 고밀도 묘사", "클리프행어/도파민 극대화"]
    )
    target_length = st.select_slider(
        "생성 분량 목표",
        options=["간략 요약 (~1,000자)", "단편/기본 (~2,500자)", "웹소설 1화 표준 (~4,500자)", "초장문 고밀도 (~6,000자 이상)"],
        value="웹소설 1화 표준 (~4,500자)"
    )

# 2. 세션 상태 초기화
fields = ["custom_lore", "worldview", "synopsis", "characters", "plot", "episodes", "notes"]
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

# 4. 실시간 자동 저장
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

system_prompt_addon = f"""
[집필 및 제어 가이드라인]
- 표현 수위: {rating_level}
- 문체 스타일: {detail_style}
- 목표 분량: {target_length}
- 작가가 직접 입력한 고유 설정(인물/세계관/배경)을 최우선 절대 규칙으로 적용할 것.
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
    "🌍 작가 고유 설정 & 세계관", 
    "🎲 시놉시스", 
    "👥 등장인물 설정", 
    "🗺️ 플롯 & 트리트먼트", 
    "📖 본문 집필 & 메모"
])

# 탭 1: 작가 고유 설정 입력 창구 & 세계관
with tab1:
    st.subheader("📌 작가 고유 설정 직접 입력 창구")
    st.markdown("직접 구상하신 **메모, 캐릭터 설정, 줄거리, 고유 세계관 규칙**을 자유롭게 붙여넣으세요. 모든 AI 생성에 기본 베이스로 적용됩니다.")
    
    # 텍스트 파일 불러오기 기능
    txt_file = st.file_uploader("텍스트 설정 파일(.txt) 불러오기", type=["txt"])
    if txt_file is not None:
        try:
            st.session_state.custom_lore = txt_file.read().decode("utf-8")
            st.success("설정 파일을 불러왔습니다!")
        except Exception as e:
            st.error(f"파일 읽기 오류: {e}")

    st.session_state.custom_lore = st.text_area(
        "✍️ 내가 만든 고유 설정집 (자유 입력)", 
        value=st.session_state.custom_lore, 
        placeholder="예:\n- 주인공: 이육사 (실종 수사관, 침착하지만 집요함)\n- 조력자: 추수국 (추적자, 거칠지만 의리 있음)\n- 배경: 2026년 도심 이면에 숨겨진 범죄 조직과 황대수의 흔적 추적\n- 고유 룰: ...",
        height=250
    )

    st.markdown("---")
    st.subheader("🌍 AI 세계관 확장 및 보완")
    col1, col2 = st.columns(2)
    with col1:
        genre = st.selectbox("장르", ["판타지", "현대판타지", "무협", "로맨스판타지", "SF", "미스터리/스릴러", "다크판타지", "기타"])
        tone = st.text_input("분위기/톤앤매너", placeholder="예: 하드보일드, 긴장감 넘치는 추적")
    with col2:
        concept = st.text_area("보완할 키워드/테마", placeholder="예: 세력 간 암투, 고유 능력의 한계")

    if st.button("🌍 내 설정 기반으로 세계관 체계화/확장"):
        with st.spinner("작가의 설정을 반영하여 세계관을 구축 중입니다..."):
            try:
                p = f"작가가 직접 입력한 고유 설정:\n{st.session_state.custom_lore}\n\n장르: {genre}\n톤: {tone}\n추가 테마: {concept}\n위 작가 설정을 절대적으로 유지하면서 세부 사회구조, 세력도, 규칙을 확장해줘."
                st.session_state.worldview = generate_ai(p)
                st.rerun()
            except Exception as e:
                st.error(f"오류: {e}")

    st.session_state.worldview = st.text_area("체계화된 세계관 설정집", value=st.session_state.worldview, height=200)

# 탭 2: 시놉시스
with tab2:
    st.subheader("🎲 시놉시스 생성")
    synop_keyword = st.text_input("시놉시스 추가 사건/키워드", placeholder="예: 황대수의 단서를 발견하고 첫 번째 수색 시작")

    if st.button("🎲 내 설정 반영하여 시놉시스 주사위 굴리기"):
        with st.spinner("시놉시스 생성 중..."):
            try:
                p = f"[작가 고유 설정]\n{st.session_state.custom_lore}\n\n[확장 세계관]\n{st.session_state.worldview}\n\n[추가 사건 키워드]: {synop_keyword}\n위 설정을 반드시 반영하여 흥미진진한 메인 시놉시스를 작성해줘."
                st.session_state.synopsis = generate_ai(p)
                st.rerun()
            except Exception as e:
                st.error(f"오류: {e}")

    st.session_state.synopsis = st.text_area("메인 시놉시스", value=st.session_state.synopsis, height=300)

# 탭 3: 캐릭터
with tab3:
    st.subheader("👥 등장인물 설정집")
    char_desc = st.text_input("추가 설계할 인물", placeholder="예: 주변 조력자, 용의자")

    if st.button("👥 캐릭터 프로필 상세화"):
        with st.spinner("등장인물 설계 중..."):
            try:
                p = f"[작가 고유 설정]\n{st.session_state.custom_lore}\n\n[시놉시스]\n{st.session_state.synopsis}\n\n[추가 요청]: {char_desc}\n작가 설정에 나온 인물들의 개성과 관계를 바탕으로 상세 프로필을 작성해줘."
                st.session_state.characters = generate_ai(p)
                st.rerun()
            except Exception as e:
                st.error(f"오류: {e}")

    st.session_state.characters = st.text_area("등장인물 상세 설정", value=st.session_state.characters, height=300)

# 탭 4: 플롯
with tab4:
    st.subheader("🗺️ 전체 플롯 & 트리트먼트")
    plot_goal = st.text_input("플롯 전개 방향", placeholder="예: 1~5화 도입부 및 추격 시작")

    if st.button("🗺️ 회차별 플롯 설계"):
        with st.spinner("플롯 구성 중..."):
            try:
                p = f"[작가 고유 설정]\n{st.session_state.custom_lore}\n\n[시놉시스]\n{st.session_state.synopsis}\n\n[인물]\n{st.session_state.characters}\n\n[전개 방향]: {plot_goal}\n각 화별 발단-전개-위기-절정-결말 및 엔딩 클리프행어를 설계해줘."
                st.session_state.plot = generate_ai(p)
                st.rerun()
            except Exception as e:
                st.error(f"오류: {e}")

    st.session_state.plot = st.text_area("회차별 플롯/트리트먼트", value=st.session_state.plot, height=300)

# 탭 5: 본문 및 집필
with tab5:
    st.subheader("📖 에피소드 집필 & 작가 메모")
    ep_num = st.text_input("회차 및 목표", placeholder="예: 제1화 - 빗속의 첫 단서")

    if st.button("📖 본문 초안 작성"):
        with st.spinner("웹소설 본문 집필 중..."):
            try:
                p = f"[작가 고유 설정]\n{st.session_state.custom_lore}\n\n[등장인물]\n{st.session_state.characters}\n\n[플롯]\n{st.session_state.plot}\n\n[이번 회차]: {ep_num}\n작가 설정을 엄격히 준수하여 1화 분량의 본문을 작성해줘."
                st.session_state.episodes = generate_ai(p)
                st.rerun()
            except Exception as e:
                st.error(f"오류: {e}")

    st.session_state.episodes = st.text_area("작성된 소설 본문", value=st.session_state.episodes, height=350)
    st.session_state.notes = st.text_area("💡 작가 메모 / 떡밥 수첩", value=st.session_state.notes, height=150)
