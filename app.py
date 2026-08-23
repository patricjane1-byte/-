import streamlit as st
import json
import streamlit.components.v1 as components
from google import genai
from google.genai import types

st.set_page_config(page_title="웹소설 스튜디오 Pro", layout="wide")

# 1. API 키 연동
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

# 2. 세션 상태 데이터 초기화
data_fields = [
    "custom_story_lore", "worldview", "synopsis", 
    "custom_char_lore", "characters", "plot", "notes",
    "foreshadowing_list"
]
for f in data_fields:
    if f not in st.session_state:
        st.session_state[f] = ""

if "episode_list" not in st.session_state:
    st.session_state.episode_list = {}
if "selected_episodes" not in st.session_state:
    st.session_state.selected_episodes = []

if "current_ep_title" not in st.session_state:
    st.session_state.current_ep_title = "제1화 - 시작"
if "current_ep_content" not in st.session_state:
    st.session_state.current_ep_content = ""

# 3. 사이드바: 📚 회차 서재 & 백업
with st.sidebar:
    st.markdown("---")
    st.subheader("📚 집필된 회차 서재")
    
    if st.session_state.episode_list:
        ep_titles = list(st.session_state.episode_list.keys())
        
        st.session_state.selected_episodes = st.multiselect(
            "🔗 AI 생성에 반영할 회차 선택 (체크)",
            options=ep_titles,
            default=st.session_state.selected_episodes,
            help="체크된 회차 본문이 프롬프트 맥락으로 자동 주입됩니다."
        )
        
        selected_ep = st.selectbox("불러올 회차 선택", options=ep_titles)
        col_load, col_del = st.columns(2)
        with col_load:
            if st.button("📖 회차 열기"):
                st.session_state.current_ep_title = selected_ep
                st.session_state.current_ep_content = st.session_state.episode_list[selected_ep]
                st.rerun()
        with col_del:
            if st.button("🗑️ 선택 삭제"):
                del st.session_state.episode_list[selected_ep]
                if selected_ep in st.session_state.selected_episodes:
                    st.session_state.selected_episodes.remove(selected_ep)
                st.rerun()
    else:
        st.info("아직 저장된 회차가 없습니다.")

    st.markdown("---")
    st.subheader("💾 데이터 백업 & 복원")
    
    uploaded_file = st.file_uploader("백업 파일 (.json) 불러오기", type=["json"])
    if uploaded_file is not None:
        try:
            data = json.load(uploaded_file)
            for f in data_fields:
                st.session_state[f] = data.get(f, "")
            st.session_state.episode_list = data.get("episode_list", {})
            st.session_state.selected_episodes = data.get("selected_episodes", [])
            st.success("백업 데이터를 성공적으로 불러왔습니다!")
        except Exception as e:
            st.error(f"파일 불러오기 오류: {e}")

    current_project = {f: st.session_state[f] for f in data_fields}
    current_project["episode_list"] = st.session_state.episode_list
    current_project["selected_episodes"] = st.session_state.selected_episodes

    project_json = json.dumps(current_project, ensure_ascii=False, indent=2)
    st.download_button(
        label="📥 전체 프로젝트 백업 (JSON)",
        data=project_json,
        file_name="webnovel_universe_backup.json",
        mime="application/json"
    )

    if st.button("⚠️ 브라우저 자동 저장 초기화"):
        components.html(
            """
            <script>
                localStorage.removeItem('novel_studio_backup_v5');
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
        const hasData = Object.values(currentData).some(v => v !== "" && Object.keys(v).length > 0);
        if (hasData) {{
            localStorage.setItem('novel_studio_backup_v5', JSON.stringify(currentData));
        }}
    </script>
    """,
    height=0
)

# 5. 메인 화면 & API 클라이언트
st.title("✍️ 웹소설 유니버스 & 스튜디오 Pro")

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
- 포함된 작가 설정 및 기작성된 회차의 인물 관계/복선 맥락을 최우선 준수할 것.
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

# 프롬프트 조립 함수
def build_context_prompt(use_story=True, use_wv=True, use_char_lore=True, use_chars=True, use_synop=True, use_plot=True, use_selected_eps=True, use_foreshadow=True):
    ctx = []
    if use_story and st.session_state.custom_story_lore.strip():
        ctx.append(f"[작가 고유 스토리/세계관 설정]\n{st.session_state.custom_story_lore}")
    if use_wv and st.session_state.worldview.strip():
        ctx.append(f"[확장 세계관]\n{st.session_state.worldview}")
    if use_char_lore and st.session_state.custom_char_lore.strip():
        ctx.append(f"[작가 고유 캐릭터 설정/주인공 프로필]\n{st.session_state.custom_char_lore}")
    if use_chars and st.session_state.characters.strip():
        ctx.append(f"[등장인물 상세 설정집]\n{st.session_state.characters}")
    if use_synop and st.session_state.synopsis.strip():
        ctx.append(f"[메인 시놉시스]\n{st.session_state.synopsis}")
    if use_plot and st.session_state.plot.strip():
        ctx.append(f"[플롯 및 트리트먼트]\n{st.session_state.plot}")
    if use_foreshadow and st.session_state.foreshadowing_list.strip():
        ctx.append(f"[추적 중인 복선 및 떡밥 목록]\n{st.session_state.foreshadowing_list}")
    
    if use_selected_eps and st.session_state.selected_episodes:
        ep_texts = []
        for title in st.session_state.selected_episodes:
            if title in st.session_state.episode_list:
                ep_texts.append(f"<{title}>\n{st.session_state.episode_list[title]}")
        if ep_texts:
            ctx.append("[기작성된 이전 회차 내용 (연계 참조)]\n" + "\n\n".join(ep_texts))
            
    return "\n\n".join(ctx)

# 탭 구성 (기존 5개 + 6번 도구 탭 추가)
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🌍 1. 스토리/세계관 설정", 
    "👥 2. 인물 설정 (원안/확장)", 
    "🎲 3. 시놉시스", 
    "🗺️ 4. 플롯 & 트리트먼트", 
    "📖 5. 본문 집필 & 서재 저장",
    "🛠️ 6. 작가 전문 집필 도구 (고급 엔진)"
])

# 탭 1: 스토리 설정
with tab1:
    st.subheader("📌 1-1. 내가 만든 고유 스토리/세계관 설정")
    txt_story = st.file_uploader("스토리 설정 파일(.txt) 불러오기", type=["txt"], key="txt_story")
    if txt_story is not None:
        try:
            st.session_state.custom_story_lore = txt_story.read().decode("utf-8")
            st.success("스토리 설정을 불러왔습니다!")
        except Exception as e:
            st.error(f"파일 읽기 오류: {e}")
    st.session_state.custom_story_lore = st.text_area(
        "작가 고유 스토리/배경 원안 (자유 입력)", 
        value=st.session_state.custom_story_lore, 
        placeholder="예: 사건의 배경, 범죄 조직의 실체, 고유 규칙, 미스터리 등",
        height=200
    )

    st.markdown("---")
    st.subheader("🌍 1-2. AI 세계관 확장 및 규칙 체계화")
    col1, col2 = st.columns(2)
    with col1:
        genre = st.selectbox("장르", ["판타지", "현대판타지", "무협", "로맨스판타지", "SF", "미스터리/스릴러", "다크판타지", "기타"])
        tone = st.text_input("분위기/톤앤매너", placeholder="예: 하드보일드, 긴장감 넘치는 추적")
    with col2:
        concept = st.text_area("보완할 키워드/테마", placeholder="예: 세력 간 암투, 고유 능력의 한계")

    use_story_for_wv = st.checkbox("🔗 [접근 제어] 고유 스토리 설정을 반영하여 확장", value=True, key="acc_wv_story")
    
    if st.button("🌍 세계관 확장 생성"):
        with st.spinner("세계관을 구축 중입니다..."):
            try:
                base_ctx = f"작가의 고유 스토리 설정:\n{st.session_state.custom_story_lore}\n\n" if use_story_for_wv else ""
                p = f"{base_ctx}장르: {genre}\n톤: {tone}\n추가 테마: {concept}\n위 내용을 바탕으로 세부 사회구조, 세력도, 규칙을 확장해줘."
                st.session_state.worldview = generate_ai(p)
                st.rerun()
            except Exception as e:
                st.error(f"오류: {e}")

    st.session_state.worldview = st.text_area("확장된 세계관 설정집", value=st.session_state.worldview, height=200)

# 탭 2: 인물 설정
with tab2:
    st.subheader("📌 2-1. 내가 만든 고유 캐릭터 원안")
    txt_char = st.file_uploader("인물 설정 파일(.txt) 불러오기", type=["txt"], key="txt_char")
    if txt_char is not None:
        try:
            st.session_state.custom_char_lore = txt_char.read().decode("utf-8")
            st.success("인물 설정을 불러왔습니다!")
        except Exception as e:
            st.error(f"파일 읽기 오류: {e}")
    st.session_state.custom_char_lore = st.text_area(
        "작가 고유 인물 원안 (주인공, 조력자, 핵심 빌런)", 
        value=st.session_state.custom_char_lore, 
        placeholder="예:\n- 주인공: 이육사 (실종 수사관)\n- 조력자: 추수국 (추적자)\n- 빌런: 황대수",
        height=200
    )

    st.markdown("---")
    st.subheader("👥 2-2. 등장인물 프로필 상세화 및 조연 확장")
    char_desc = st.text_input("추가/보완 요청 사항", placeholder="예: 주요 인물 프로필 완성, 신규 조력자 2명 추가")

    c1, c2, c3 = st.columns(3)
    with c1:
        use_char_lore_for_c = st.checkbox("🔗 고유 캐릭터 원안 반영", value=True, key="acc_c_char")
    with c2:
        use_story_for_c = st.checkbox("🔗 고유 스토리 설정 반영", value=True, key="acc_c_story")
    with c3:
        use_wv_for_c = st.checkbox("🔗 확장 세계관 반영", value=True, key="acc_c_wv")

    if st.button("👥 캐릭터 프로필 생성 및 확장"):
        with st.spinner("등장인물 설계 중..."):
            try:
                ctx = build_context_prompt(
                    use_story=use_story_for_c, 
                    use_wv=use_wv_for_c, 
                    use_char_lore=use_char_lore_for_c, 
                    use_chars=False, use_synop=False, use_plot=False, use_selected_eps=False, use_foreshadow=False
                )
                p = f"{ctx}\n\n[추가 요청]: {char_desc}\n위 설정을 기반으로 인물들의 상세 프로필을 작성해줘."
                st.session_state.characters = generate_ai(p)
                st.rerun()
            except Exception as e:
                st.error(f"오류: {e}")

    st.session_state.characters = st.text_area("완성된 등장인물 상세 설정집", value=st.session_state.characters, height=250)

# 탭 3: 시놉시스
with tab3:
    st.subheader("🎲 3. 시놉시스 생성")
    synop_keyword = st.text_input("시놉시스 핵심 사건 키워드", placeholder="예: 단서 발견 및 본격 추적 시작")

    st.markdown("**접근 여부 설정 (프롬프트 반영 항목)**")
    sc1, sc2, sc3, sc4, sc5 = st.columns(5)
    with sc1:
        use_s_story = st.checkbox("고유 스토리", value=True, key="syn_story")
    with sc2:
        use_s_wv = st.checkbox("확장 세계관", value=True, key="syn_wv")
    with sc3:
        use_s_char_lore = st.checkbox("캐릭터 원안", value=True, key="syn_char_lore")
    with sc4:
        use_s_chars = st.checkbox("상세 인물집", value=True, key="syn_chars")
    with sc5:
        use_s_eps = st.checkbox("체크된 회차 글", value=True, key="syn_eps")

    if st.button("🎲 시놉시스 주사위 굴리기"):
        with st.spinner("시놉시스 생성 중..."):
            try:
                ctx = build_context_prompt(
                    use_story=use_s_story, 
                    use_wv=use_s_wv, 
                    use_char_lore=use_s_char_lore, 
                    use_chars=use_s_chars, 
                    use_synop=False, use_plot=False,
                    use_selected_eps=use_s_eps,
                    use_foreshadow=True
                )
                p = f"{ctx}\n\n[추가 키워드]: {synop_keyword}\n선택된 설정들과 회차 맥락을 반영하여 메인 시놉시스를 작성해줘."
                st.session_state.synopsis = generate_ai(p)
                st.rerun()
            except Exception as e:
                st.error(f"오류: {e}")

    st.session_state.synopsis = st.text_area("메인 시놉시스", value=st.session_state.synopsis, height=300)

# 탭 4: 플롯
with tab4:
    st.subheader("🗺️ 4. 회차별 플롯 & 트리트먼트")
    plot_goal = st.text_input("플롯 전개 범위", placeholder="예: 다음 화 전개 방향 및 위기 상황")

    st.markdown("**접근 여부 설정 (프롬프트 반영 항목)**")
    pc1, pc2, pc3, pc4, pc5, pc6 = st.columns(6)
    with pc1:
        use_p_story = st.checkbox("고유 스토리", value=True, key="plot_story")
    with pc2:
        use_p_wv = st.checkbox("세계관", value=True, key="plot_wv")
    with pc3:
        use_p_char = st.checkbox("캐릭터 원안", value=True, key="plot_char_lore")
    with pc4:
        use_p_chars = st.checkbox("상세 인물집", value=True, key="plot_chars")
    with pc5:
        use_p_syn = st.checkbox("시놉시스", value=True, key="plot_syn")
    with pc6:
        use_p_eps = st.checkbox("체크된 회차 글", value=True, key="plot_eps")

    if st.button("🗺️ 회차별 플롯 설계"):
        with st.spinner("플롯 구성 중..."):
            try:
                ctx = build_context_prompt(
                    use_story=use_p_story, 
                    use_wv=use_p_wv, 
                    use_char_lore=use_p_char, 
                    use_chars=use_p_chars, 
                    use_synop=use_p_syn, 
                    use_plot=False,
                    use_selected_eps=use_p_eps,
                    use_foreshadow=True
                )
                p = f"{ctx}\n\n[전개 목표]: {plot_goal}\n기존 회차의 결말과 사건을 이어받아 다음 전개 플롯 및 클리프행어를 설계해줘."
                st.session_state.plot = generate_ai(p)
                st.rerun()
            except Exception as e:
                st.error(f"오류: {e}")

    st.session_state.plot = st.text_area("회차별 플롯/트리트먼트", value=st.session_state.plot, height=300)

# 탭 5: 본문 집필
with tab5:
    st.subheader("📖 5. 에피소드 집필 & 서재 보관")
    st.session_state.current_ep_title = st.text_input("집필 회차 제목", value=st.session_state.current_ep_title, placeholder="예: 제2화 - 추적의 시작")

    st.markdown("**접근 여부 설정 (프롬프트 반영 항목)**")
    ec1, ec2, ec3, ec4, ec5, ec6, ec7 = st.columns(7)
    with ec1:
        use_e_story = st.checkbox("스토리", value=True, key="ep_story")
    with ec2:
        use_e_wv = st.checkbox("세계관", value=True, key="ep_wv")
    with ec3:
        use_e_char = st.checkbox("인물 원안", value=True, key="ep_char_lore")
    with ec4:
        use_e_chars = st.checkbox("상세 인물집", value=True, key="ep_chars")
    with ec5:
        use_e_syn = st.checkbox("시놉시스", value=True, key="ep_syn")
    with ec6:
        use_e_plot = st.checkbox("플롯", value=True, key="ep_plot")
    with ec7:
        use_e_eps = st.checkbox("체크된 회차 글", value=True, key="ep_eps")

    col_gen, col_save = st.columns([1, 1])
    with col_gen:
        if st.button("📖 AI 본문 초안 작성"):
            with st.spinner("웹소설 본문 집필 중..."):
                try:
                    ctx = build_context_prompt(
                        use_story=use_e_story, 
                        use_wv=use_e_wv, 
                        use_char_lore=use_e_char, 
                        use_chars=use_e_chars, 
                        use_synop=use_e_syn, 
                        use_plot=use_e_plot,
                        use_selected_eps=use_e_eps,
                        use_foreshadow=True
                    )
                    p = f"{ctx}\n\n[이번 회차 집필 요청]: {st.session_state.current_ep_title}\n기작성된 이전 회차의 맥락을 자연스럽게 이어받아 1화 분량의 본문을 완성해줘."
                    st.session_state.current_ep_content = generate_ai(p)
                    st.session_state.episode_list[st.session_state.current_ep_title] = st.session_state.current_ep_content
                    st.rerun()
                except Exception as e:
                    st.error(f"오류: {e}")

    with col_save:
        if st.button("💾 현재 수정한 내용을 서재에 저장/업데이트"):
            st.session_state.episode_list[st.session_state.current_ep_title] = st.session_state.current_ep_content
            st.success(f"'{st.session_state.current_ep_title}' 서재 저장 완료!")
            st.rerun()

    st.session_state.current_ep_content = st.text_area("작성된 소설 본문", value=st.session_state.current_ep_content, height=400)
    st.session_state.notes = st.text_area("💡 작가 메모 / 아이디어 수첩", value=st.session_state.notes, height=120)

# 탭 6: 고급 작가 엔진 도구함 (신규 추가)
with tab6:
    st.subheader("🛠️ 작가 전문 집필 & 분석 도구함")
    
    # 1. 설정 붕괴 탐지기
    with st.expander("🔍 1. 설정 오류 & 붕괴 탐지기 (Continuity Guard)", expanded=True):
        st.markdown("현재 본문과 **[원안 설정집 + 이전 회차]**를 비교하여 인물 성격 오류, 모순, 시간대 불일치를 검증합니다.")
        if st.button("🔍 현재 본문 설정 오류 검사"):
            with st.spinner("설정 및 복선 정합성을 검증 중입니다..."):
                try:
                    ctx = build_context_prompt(use_story=True, use_wv=True, use_char_lore=True, use_chars=True, use_synop=True, use_plot=True, use_selected_eps=True, use_foreshadow=True)
                    p = f"""{ctx}
                    
[검증 대상 본문]:
{st.session_state.current_ep_content}

위 본문이 앞선 설정(인물 말투/외모/능력, 세계관 법칙, 이전 회차 사건)과 충돌하거나 모순되는 점이 있는지 아래 양식으로 정밀 분석해줘:
1. ⚠️ 발견된 설정 오류 및 모순점 (없다면 없음)
2. 🎭 인물 개성 및 어투 일관성 점검
3. 💡 수정 추천 방안"""
                    report = generate_ai(p)
                    st.info(report)
                except Exception as e:
                    st.error(f"검증 오류: {e}")

    # 2. 분기형 클리프행어
    with st.expander("⚡ 2. 3가지 분기형 클리프행어(절단신공) 생성기"):
        st.markdown("현재 본문의 결말부에 붙일 수 있는 **3가지 독자 유입용 엔딩 훅**을 생성합니다.")
        if st.button("⚡ 엔딩 분기 3종 생성"):
            with st.spinner("독자 몰입형 엔딩 훅을 계산 중입니다..."):
                try:
                    ctx = build_context_prompt(use_story=False, use_wv=False, use_char_lore=True, use_chars=True, use_synop=True, use_plot=False, use_selected_eps=False)
                    p = f"""{ctx}
                    
[현재 본문]:
{st.session_state.current_ep_content}

위 본문의 마지막 상황에서 이어질 수 있는 다음 3가지 유형의 '강렬한 클리프행어(절단신공) 결말 문단'을 작성해줘:
- [A안: 충격/반전형] 숨겨진 비밀이나 새로운 용의자/단서의 급작스러운 등장
- [B안: 절체절명 위기형] 주인공의 목숨이나 핵심 계획이 위협받는 긴박한 순간 단절
- [C안: 심리/갈등 격돌형] 인물 간의 관계가 깨지거나 숨겨진 본심이 터져 나오는 순간 단절"""
                    st.session_state.cliffhangers = generate_ai(p)
                    st.success("엔딩 분기가 생성되었습니다!")
                except Exception as e:
                    st.error(f"오류: {e}")
        if "cliffhangers" in st.session_state:
            st.text_area("생성된 엔딩 훅 3종", value=st.session_state.cliffhangers, height=250)

    # 3. 특정 문단 정밀 윤문 도구
    with st.expander("🎯 3. 문단 정밀 퇴고 및 윤문 도구 (Surgical Rewriter)"):
        st.markdown("고치고 싶은 특정 문장이나 대화만 붙여넣어 즉시 업그레이드합니다.")
        target_paragraph = st.text_area("수정할 문단/대화 붙여넣기", placeholder="수정하고 싶은 특정 문장을 여기에 넣으세요.")
        rewrite_goal = st.selectbox("윤문 방향", [
            "대사를 더 날카롭고 매력적인 톤으로 변경",
            "격투/추격 액션의 속도감과 타격감 강화",
            "감각적 묘사(시각/청각/심리) 고밀도 추가",
            "웹소설 가독성에 맞게 짧고 리듬감 있는 문장으로 교체"
        ])
        if st.button("🎯 해당 문단만 정밀 재작성"):
            if target_paragraph.strip():
                with st.spinner("문단을 다듬는 중입니다..."):
                    try:
                        p = f"[수정 요청]: {rewrite_goal}\n[원문 문단]:\n{target_paragraph}\n\n위 문단을 요청사항에 맞게 웹소설 프로 작가 수준으로 윤문해줘."
                        rewritten = generate_ai(p)
                        st.text_area("✨ 윤문된 결과", value=rewritten, height=180)
                    except Exception as e:
                        st.error(f"오류: {e}")
            else:
                st.warning("수정할 문단을 입력해 주세요.")

    # 4. 복선 & 떡밥 트래커
    with st.expander("🪢 4. 복선(떡밥) & 미회수 단서 트래커"):
        st.markdown("작품 전체에 뿌려진 떡밥을 기록하고 회수 상태를 관리합니다. 여기에 적힌 내용은 모든 AI 생성 시 맥락으로 전달됩니다.")
        
        col_t1, col_t2 = st.columns([1, 1])
        with col_t1:
            if st.button("🔍 현재 회차들에서 뿌려진 떡밥 자동 추출"):
                with st.spinner("회차 본문에서 복선을 수집 중입니다..."):
                    try:
                        ep_all = "\n\n".join([f"<{k}>\n{v}" for k, v in st.session_state.episode_list.items()])
                        p = f"[전체 회차 본문]\n{ep_all}\n\n위 본문들에 등장한 핵심 단서, 의문의 인물, 미해결 사건 등 작가가 회수해야 할 '복선/떡밥 목록'을 번호 매겨 체계적으로 정리해줘."
                        st.session_state.foreshadowing_list = generate_ai(p)
                        st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")
        
        st.session_state.foreshadowing_list = st.text_area(
            "📌 추적 중인 복선 및 떡밥 목록", 
            value=st.session_state.foreshadowing_list, 
            placeholder="예:\n- [미회수] 1화: 피 묻은 회중시계의 원래 주인\n- [미회수] 2화: 황대수가 남긴 암호 쪽지\n- [회수완료] 3화: 정보원의 진짜 정체",
            height=200
        )

    # 5. 시점(POV) 전환기
    with st.expander("🎭 5. 1인칭 주인공 / 관찰자 시점(POV) 전환기"):
        st.markdown("현재 본문을 다른 인물의 시점(1인칭 나, 3인칭 관찰자, 빌런 시점)으로 다시 씁니다.")
        pov_target = st.selectbox("변환할 시점", [
            "주인공 1인칭 시점 (내면 심리 극대화)",
            "조력자/추적자 시점에서 바라본 주인공 (3인칭 관찰자)",
            "빌런/상대방 시점 (이면의 음모와 긴장감)",
            "전지적 작가 시점 (객관적/웅장한 묘사)"
        ])
        if st.button("🎭 선택한 시점으로 본문 변환"):
            with st.spinner("시점을 전환하여 재집필 중입니다..."):
                try:
                    p = f"[원문 본문]:\n{st.session_state.current_ep_content}\n\n[요청]: 위 장면을 '{pov_target}'으로 재해석하여 새로운 시각의 본문으로 다시 작성해줘."
                    pov_result = generate_ai(p)
                    st.text_area("🎭 시점 변환 본문 결과", value=pov_result, height=350)
                except Exception as e:
                    st.error(f"오류: {e}")
