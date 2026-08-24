import streamlit as st
import json
import os
from google import genai
from google.genai import types

st.set_page_config(page_title="웹소설 스튜디오 Pro Max", layout="wide")

# ==========================================
# 0. 영구 자동 저장 데이터 파일 시스템 (절대 리셋 방지)
# ==========================================
DATA_FILE = "novel_project_data.json"

default_data = {
    "custom_story_lore": "",
    "worldview": "",
    "synopsis": "",
    "custom_char_lore": "",
    "characters": "",
    "plot": "",
    "notes": "",
    "foreshadowing_list": "",
    "compressed_summaries": "",
    "episode_list": {},
    "selected_episodes": [],
    "current_ep_title": "제1화 - 시작",
    "current_ep_content": ""
}

def load_saved_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                for k, v in default_data.items():
                    if k not in saved:
                        saved[k] = v
                return saved
        except Exception:
            return default_data.copy()
    return default_data.copy()

def save_all_data():
    save_payload = {k: st.session_state.get(k, default_data[k]) for k in default_data.keys()}
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(save_payload, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.sidebar.error(f"저장 오류: {e}")

# 초기 구동 시 저장된 파일에서 세션 상태 복원
if "initialized" not in st.session_state:
    saved_state = load_saved_data()
    for k, v in saved_state.items():
        st.session_state[k] = v
    st.session_state.initialized = True

# 1. API 키 연동 (Secrets 1순위 -> 수동 입력 2순위)
api_key = st.secrets.get("GEMINI_API_KEY", "")

# 사이드바 제어판
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

    st.markdown("---")
    st.subheader("📚 회차 서재")
    if st.session_state.episode_list:
        ep_titles = list(st.session_state.episode_list.keys())
        st.session_state.selected_episodes = st.multiselect(
            "🔗 AI 생성에 반영할 회차 선택 (체크)",
            options=ep_titles,
            default=st.session_state.selected_episodes,
            on_change=save_all_data
        )
        selected_ep = st.selectbox("불러올 회차 선택", options=ep_titles)
        col_load, col_del = st.columns(2)
        with col_load:
            if st.button("📖 회차 열기"):
                st.session_state.current_ep_title = selected_ep
                st.session_state.current_ep_content = st.session_state.episode_list[selected_ep]
                save_all_data()
                st.rerun()
        with col_del:
            if st.button("🗑️ 회차 삭제"):
                del st.session_state.episode_list[selected_ep]
                if selected_ep in st.session_state.selected_episodes:
                    st.session_state.selected_episodes.remove(selected_ep)
                save_all_data()
                st.rerun()

        # 전체 TXT 다운로드
        full_novel_text = "\n\n" + "="*40 + "\n\n"
        combined_text = full_novel_text.join([f"[{title}]\n\n{content}" for title, content in st.session_state.episode_list.items()])
        st.download_button(
            label="📄 전체 소설 통합 TXT 다운로드",
            data=combined_text,
            file_name="full_novel_series.txt",
            mime="text/plain"
        )
    else:
        st.info("저장된 회차가 없습니다.")

# 메인 화면 상단 헤더
st.title("✍️ 웹소설 유니버스 & 스튜디오 Pro Max")
st.caption("🔒 모든 고유 설정, 인물 원안, 회차 본문은 입력/수정 즉시 영구 자동 저장됩니다.")

if not api_key:
    st.warning("👈 좌측 상단 화살표(>>)를 눌러 사이드바에 Gemini API Key를 입력해 주세요.")
    st.stop()

client = genai.Client(api_key=api_key)
MODEL_NAME = "gemini-3.6-flash"

system_prompt_addon = f"""
[집필 및 제어 가이드라인]
- 표현 수위: {rating_level}
- 문체 스타일: {detail_style}
- 목표 분량: {target_length}
- 포함된 작가 설정, 인물 관계, 복선 맥락을 최우선 준수할 것.
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

def build_context_prompt(use_story=True, use_wv=True, use_char_lore=True, use_chars=True, use_synop=True, use_plot=True, use_selected_eps=True, use_foreshadow=True, use_compressed=True):
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
    if use_compressed and st.session_state.compressed_summaries.strip():
        ctx.append(f"[전체 회차 3줄 압축 줄거리 요약본]\n{st.session_state.compressed_summaries}")
    
    if use_selected_eps and st.session_state.selected_episodes:
        ep_texts = []
        for title in st.session_state.selected_episodes:
            if title in st.session_state.episode_list:
                ep_texts.append(f"<{title}>\n{st.session_state.episode_list[title]}")
        if ep_texts:
            ctx.append("[기작성된 이전 회차 내용 (연계 참조)]\n" + "\n\n".join(ep_texts))
            
    return "\n\n".join(ctx)

def select_target_text(prefix_key):
    st.markdown("🎯 **대상 본문 선택**")
    options = ["현재 작업 중인 본문 (5번 탭)"]
    if st.session_state.episode_list:
        options.append("서재에 저장된 회차 선택")
    options.append("텍스트 직접 붙여넣기")
    
    src_type = st.radio("대상 선택", options=options, key=f"{prefix_key}_src_type", horizontal=True)
    
    target_text = ""
    if src_type == "현재 작업 중인 본문 (5번 탭)":
        target_text = st.session_state.current_ep_content
    elif src_type == "서재에 저장된 회차 선택":
        ep_keys = list(st.session_state.episode_list.keys())
        chosen_ep = st.selectbox("회차 선택", options=ep_keys, key=f"{prefix_key}_chosen_ep")
        target_text = st.session_state.episode_list.get(chosen_ep, "")
    else:
        target_text = st.text_area("텍스트 입력", placeholder="분석할 본문이나 특정 장면을 붙여넣으세요.", key=f"{prefix_key}_custom_text", height=120)
        
    return target_text

# 탭 메뉴
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
            save_all_data()
            st.success("스토리 설정을 불러왔습니다!")
        except Exception as e:
            st.error(f"파일 읽기 오류: {e}")
            
    val_story = st.text_area(
        "작가 고유 스토리/배경 원안 (자동 저장됨)", 
        value=st.session_state.custom_story_lore, 
        placeholder="예: 사건의 배경, 범죄 조직의 실체, 고유 규칙, 미스터리 등",
        height=250,
        key="input_custom_story"
    )
    if val_story != st.session_state.custom_story_lore:
        st.session_state.custom_story_lore = val_story
        save_all_data()

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
                save_all_data()
                st.rerun()
            except Exception as e:
                st.error(f"오류: {e}")

    val_wv = st.text_area("확장된 세계관 설정집", value=st.session_state.worldview, height=200, key="input_wv")
    if val_wv != st.session_state.worldview:
        st.session_state.worldview = val_wv
        save_all_data()

# 탭 2: 인물 설정
with tab2:
    st.subheader("📌 2-1. 내가 만든 고유 캐릭터 원안")
    txt_char = st.file_uploader("인물 설정 파일(.txt) 불러오기", type=["txt"], key="txt_char")
    if txt_char is not None:
        try:
            st.session_state.custom_char_lore = txt_char.read().decode("utf-8")
            save_all_data()
            st.success("인물 설정을 불러왔습니다!")
        except Exception as e:
            st.error(f"파일 읽기 오류: {e}")
            
    val_char = st.text_area(
        "작가 고유 인물 원안 (주인공, 조력자, 핵심 빌런 - 자동 저장됨)", 
        value=st.session_state.custom_char_lore, 
        placeholder="예:\n- 주인공: 백은조, 추수국\n- 빌런: 크람푸스",
        height=250,
        key="input_custom_char"
    )
    if val_char != st.session_state.custom_char_lore:
        st.session_state.custom_char_lore = val_char
        save_all_data()

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
                    use_chars=False, use_synop=False, use_plot=False, use_selected_eps=False, use_foreshadow=False, use_compressed=False
                )
                p = f"{ctx}\n\n[추가 요청]: {char_desc}\n위 설정을 기반으로 인물들의 상세 프로필을 작성해줘."
                st.session_state.characters = generate_ai(p)
                save_all_data()
                st.rerun()
            except Exception as e:
                st.error(f"오류: {e}")

    val_chars = st.text_area("완성된 등장인물 상세 설정집", value=st.session_state.characters, height=250, key="input_chars")
    if val_chars != st.session_state.characters:
        st.session_state.characters = val_chars
        save_all_data()

# 탭 3: 시놉시스
with tab3:
    st.subheader("🎲 3. 시놉시스 생성")
    
    synop_mode = st.radio("시놉시스 생성 범위", ["전체 메인 시놉시스 (작품 전체 윤곽)", "특정 회차 전용 시놉시스 (예: 제3화 단독 줄거리)"], horizontal=True)
    
    if synop_mode == "특정 회차 전용 시놉시스 (예: 제3화 단독 줄거리)":
        target_ep_name = st.text_input("목표 회차", value="제1화", placeholder="예: 제1화, 제2화 등")
        synop_keyword = st.text_input("해당 회차 핵심 사건 키워드", placeholder="예: 판게아 금고 개방과 역지원 촉탁 발주")
        prompt_instruction = f"[{target_ep_name} 단독 시놉시스 생성 요청]\n키워드: {synop_keyword}\n설정과 이전 사건을 이어받아 '{target_ep_name}'에서 일어날 단기 핵심 시놉시스를 작성해줘."
    else:
        synop_keyword = st.text_input("메인 시놉시스 핵심 사건 키워드", placeholder="예: 거액의 달란트와 프리텐더 연합군, 크람푸스 흑막 척결")
        prompt_instruction = f"[작품 전체 메인 시놉시스 생성 요청]\n키워드: {synop_keyword}\n작품 전체를 관통하는 메인 시놉시스를 작성해줘."

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
        use_s_eps = st.checkbox("체크된 회차 글", value=(synop_mode != "전체 메인 시놉시스 (작품 전체 윤곽)"), key="syn_eps")

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
                    use_foreshadow=True,
                    use_compressed=True
                )
                p = f"{ctx}\n\n{prompt_instruction}"
                st.session_state.synopsis = generate_ai(p)
                save_all_data()
                st.rerun()
            except Exception as e:
                st.error(f"오류: {e}")

    val_syn = st.text_area("시놉시스 결과", value=st.session_state.synopsis, height=300, key="input_syn")
    if val_syn != st.session_state.synopsis:
        st.session_state.synopsis = val_syn
        save_all_data()

# 탭 4: 플롯
with tab4:
    st.subheader("🗺️ 4. 회차별 플롯 & 트리트먼트")
    
    plot_mode = st.radio("플롯 설계 범위", ["특정 회차 전용 플롯 (예: 제1화 씬별 상세 전개)", "연속 회차/전체 플롯 흐름 (예: 1~5화 트리트먼트)"], horizontal=True)
    
    if plot_mode == "특정 회차 전용 플롯 (예: 제1화 씬별 상세 전개)":
        target_plot_ep = st.text_input("설계할 회차", value="제1화", placeholder="예: 제1화")
        plot_goal = st.text_input("해당 회차 전개 목표 및 위기", placeholder="예: 흑막 크람푸스의 음모 포착 및 첫 격돌")
        plot_instruction = f"[{target_plot_ep} 씬별 상세 플롯 설계]\n목표: {plot_goal}\n설정을 반영하여 '{target_plot_ep}'의 [오프닝 씬 -> 갈등 심화 -> 위기 -> 엔딩 클리프행어]를 씬 단위로 정밀하게 설계해줘."
    else:
        plot_goal = st.text_input("플롯 전개 범위 및 핵심 흐름", placeholder="예: 1~4단계 역전의 판게아 정상 결전 흐름")
        plot_instruction = f"[연속 회차 플롯 설계]\n범위: {plot_goal}\n회차별 핵심 사건과 떡밥 배치 구조를 단계별로 설계해줘."

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

    if st.button("🗺️ 플롯 설계 생성"):
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
                    use_foreshadow=True,
                    use_compressed=True
                )
                p = f"{ctx}\n\n{plot_instruction}"
                st.session_state.plot = generate_ai(p)
                save_all_data()
                st.rerun()
            except Exception as e:
                st.error(f"오류: {e}")

    val_plot = st.text_area("회차별 플롯/트리트먼트 결과", value=st.session_state.plot, height=300, key="input_plot")
    if val_plot != st.session_state.plot:
        st.session_state.plot = val_plot
        save_all_data()

# 탭 5: 본문 집필
with tab5:
    st.subheader("📖 5. 에피소드 집필 & 서재 보관")
    
    if st.session_state.episode_list:
        c_sel, c_btn = st.columns([3, 1])
        with c_sel:
            ep_to_load = st.selectbox("📂 수정할 기존 회차 선택", options=list(st.session_state.episode_list.keys()), key="load_ep_direct")
        with c_btn:
            if st.button("📥 회차 불러오기"):
                st.session_state.current_ep_title = ep_to_load
                st.session_state.current_ep_content = st.session_state.episode_list[ep_to_load]
                save_all_data()
                st.rerun()
        st.markdown("---")

    val_ep_title = st.text_input("집필 회차 제목", value=st.session_state.current_ep_title, placeholder="예: 제1화 - 운명의 시작", key="input_ep_title")
    if val_ep_title != st.session_state.current_ep_title:
        st.session_state.current_ep_title = val_ep_title
        save_all_data()

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
                        use_foreshadow=True,
                        use_compressed=True
                    )
                    p = f"{ctx}\n\n[이번 회차 집필 요청]: {st.session_state.current_ep_title}\n설정과 플롯 맥락을 반영하여 1화 분량의 소설 본문을 완성해줘."
                    st.session_state.current_ep_content = generate_ai(p)
                    st.session_state.episode_list[st.session_state.current_ep_title] = st.session_state.current_ep_content
                    save_all_data()
                    st.rerun()
                except Exception as e:
                    st.error(f"오류: {e}")

    with col_save:
        if st.button("💾 현재 수정한 내용을 서재에 저장/업데이트"):
            st.session_state.episode_list[st.session_state.current_ep_title] = st.session_state.current_ep_content
            save_all_data()
            st.success(f"'{st.session_state.current_ep_title}' 서재 저장 완료!")
            st.rerun()

    val_ep_content = st.text_area("작성된 소설 본문 (직접 편집 가능 - 자동 저장됨)", value=st.session_state.current_ep_content, height=400, key="input_ep_content")
    if val_ep_content != st.session_state.current_ep_content:
        st.session_state.current_ep_content = val_ep_content
        save_all_data()
    
    text_len_with_space = len(st.session_state.current_ep_content)
    text_len_without_space = len(st.session_state.current_ep_content.replace(" ", "").replace("\n", ""))
    read_time_min = round(text_len_with_space / 800, 1)
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("공백 포함 글자수", f"{text_len_with_space:,} 자")
    m2.metric("공백 제외 글자수", f"{text_len_without_space:,} 자")
    m3.metric("예상 독서 시간", f"약 {read_time_min} 분")
    
    status_color = "🟢 웹소설 1화 적정 규격" if 4000 <= text_len_with_space <= 6000 else ("🟡 분량 보완 필요" if text_len_with_space < 4000 else "🟠 초장문 분량")
    m4.metric("플랫폼 분량 규격", status_color)

    with st.expander("📱 스마트폰 독자 뷰어 모드 (실전 리더기 화면)"):
        st.markdown(
            f"""
            <div style="background-color: #121212; color: #E0E0E0; padding: 25px; border-radius: 12px; font-size: 17px; line-height: 2.0; font-family: 'KoPubWorldBatang', serif; max-width: 650px; margin: auto; border: 1px solid #333;">
                <h3 style="text-align: center; color: #FFF; margin-bottom: 30px;">{st.session_state.current_ep_title}</h3>
                {st.session_state.current_ep_content.replace(chr(10), '<br>')}
            </div>
            """,
            unsafe_allow_html=True
        )

    val_notes = st.text_area("💡 작가 메모 / 아이디어 수첩", value=st.session_state.notes, height=120, key="input_notes")
    if val_notes != st.session_state.notes:
        st.session_state.notes = val_notes
        save_all_data()

# 탭 6: 고급 작가 엔진 도구함
with tab6:
    st.subheader("🛠️ 작가 전문 집필 & 분석 도구함 Pro")
    
    with st.expander("🔍 1. 설정 오류 & 붕괴 탐지기 (Continuity Guard)", expanded=False):
        st.markdown("선택한 본문과 **[원안 설정집 + 이전 회차]**를 비교하여 인물 성격 오류, 모순, 시간대 불일치를 정밀 검증합니다.")
        target_guard_text = select_target_text("guard")
        
        if st.button("🔍 선택된 본문 설정 오류 검사"):
            if target_guard_text.strip():
                with st.spinner("설정 및 복선 정합성을 검증 중입니다..."):
                    try:
                        ctx = build_context_prompt(use_story=True, use_wv=True, use_char_lore=True, use_chars=True, use_synop=True, use_plot=True, use_selected_eps=True, use_foreshadow=True, use_compressed=True)
                        p = f"""{ctx}\n\n[검증 대상 본문]:\n{target_guard_text}\n\n위 본문이 설정과 충돌하거나 모순되는 점을 정밀 분석해줘:\n1. ⚠️ 발견된 설정 오류 및 모순점\n2. 🎭 인물 개성 및 어투 일관성 점검\n3. 💡 수정 추천 방안"""
                        report = generate_ai(p)
                        st.info(report)
                    except Exception as e:
                        st.error(f"검증 오류: {e}")
            else:
                st.warning("검사할 본문 내용이 없습니다.")

    with st.expander("📈 2. 독자 몰입도 & 텐션 그래프 분석기 (Pacing Analyzer)", expanded=False):
        st.markdown("선택한 본문의 **사건 전개 속도, 긴장감(텐션), 대화 vs 서술 비중, 독자 이탈 위험 구간**을 평가합니다.")
        target_pacing_text = select_target_text("pacing")
        
        if st.button("📈 텐션 및 페이싱 종합 분석 실행"):
            if target_pacing_text.strip():
                with st.spinner("도파민 및 서사 텐션을 분석 중입니다..."):
                    try:
                        p = f"""[분석 대상 본문]:\n{target_pacing_text}\n\n위 웹소설 본문의 독자 몰입도와 페이싱을 아래 항목별로 100점 만점 점수와 함께 날카롭게 진단해줘:\n1. ⚡ 사건 전개 속도 (Pacing Score)\n2. 🔥 서사적 긴장감 및 도파민 (Tension Score)\n3. 💬 대화 대 서술 비율\n4. ⚠️ 독자 이탈 위험 지점 및 템포 개선 솔루션"""
                        pacing_report = generate_ai(p)
                        st.info(pacing_report)
                    except Exception as e:
                        st.error(f"오류: {e}")
            else:
                st.warning("분석할 본문이 없습니다.")

    with st.expander("💬 3. 인물별 고유 말투(보이스) 튜너 (Character Voice Tuner)", expanded=False):
        st.markdown("특정 인물의 대사를 선택하여 **고유한 어조**로 일괄 톤 교정합니다.")
        target_voice_text = select_target_text("voice")
        target_char_name = st.text_input("교정할 캐릭터 이름", placeholder="예: 추수국, 백은조")
        voice_style = st.selectbox("적용할 말투 스타일", [
            "거칠고 날카로운 하드보일드/베테랑 형사 어조",
            "능청스럽고 여유 넘치는 건들거리는 어조",
            "감정을 철저히 억누른 냉철하고 절제된 단답형 어조",
            "걸쭉한 사투리 억양",
            "고풍스럽고 우아한 귀족/상위 계급 어조"
        ])
        if st.button("💬 해당 캐릭터 말투 일괄 튜닝"):
            if target_voice_text.strip() and target_char_name.strip():
                with st.spinner("대사 톤을 교정 중입니다..."):
                    try:
                        p = f"[본문]:\n{target_voice_text}\n\n[요청]: 위 본문에서 '{target_char_name}'의 모든 대사와 행동 묘사를 '{voice_style}' 스타일로 자연스럽고 매력적으로 교정해줘. 다른 인물의 대사는 건드리지 마."
                        st.session_state.voice_tuned_res = generate_ai(p)
                        st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")
            else:
                st.warning("본문과 캐릭터 이름을 모두 입력해 주세요.")
                
        if "voice_tuned_res" in st.session_state and st.session_state.voice_tuned_res:
            st.text_area("✨ 말투 튜닝 결과", value=st.session_state.voice_tuned_res, height=220)
            if st.button("📥 이 튜닝 결과를 5번 탭 본문으로 적용"):
                st.session_state.current_ep_content = st.session_state.voice_tuned_res
                save_all_data()
                st.success("5번 탭 본문으로 적용되었습니다!")

    with st.expander("⚡ 4. 3가지 분기형 클리프행어(절단신공) 생성기", expanded=False):
        st.markdown("선택한 본문의 결말부에 붙일 수 있는 **3가지 독자 유입용 엔딩 훅**을 생성합니다.")
        target_cliff_text = select_target_text("cliff")
        
        if st.button("⚡ 엔딩 분기 3종 생성"):
            if target_cliff_text.strip():
                with st.spinner("독자 몰입형 엔딩 훅을 계산 중입니다..."):
                    try:
                        ctx = build_context_prompt(use_story=False, use_wv=False, use_char_lore=True, use_chars=True, use_synop=True, use_plot=False, use_selected_eps=False)
                        p = f"""{ctx}\n\n[선택된 본문]:\n{target_cliff_text}\n\n위 본문의 마지막 상황에서 이어질 수 있는 3가지 유형의 '강렬한 클리프행어 결말 문단'을 작성해줘:\n- [A안: 충격/반전형]\n- [B안: 절체절명 위기형]\n- [C안: 심리/갈등 격돌형]"""
                        st.session_state.cliffhangers = generate_ai(p)
                        st.success("엔딩 분기가 생성되었습니다!")
                    except Exception as e:
                        st.error(f"오류: {e}")
            else:
                st.warning("본문 내용이 없습니다.")
                
        if "cliffhangers" in st.session_state and st.session_state.cliffhangers:
            st.text_area("생성된 엔딩 훅 3종", value=st.session_state.cliffhangers, height=220)

    with st.expander("🎯 5. 문단 정밀 퇴고 및 윤문 도구 (Surgical Rewriter)", expanded=False):
        st.markdown("고치고 싶은 특정 문장이나 대화를 선택하거나 붙여넣어 즉시 업그레이드합니다.")
        target_rewrite_text = select_target_text("rewrite")
        rewrite_goal = st.selectbox("윤문 방향", [
            "대사를 더 날카롭고 매력적인 톤으로 변경",
            "격투/추격 액션의 속도감과 타격감 강화",
            "감각적 묘사(시각/청각/심리) 고밀도 추가",
            "웹소설 가독성에 맞게 짧고 리듬감 있는 문장으로 교체"
        ])
        if st.button("🎯 해당 문단/본문 정밀 재작성"):
            if target_rewrite_text.strip():
                with st.spinner("문단을 다듬는 중입니다..."):
                    try:
                        p = f"[수정 요청]: {rewrite_goal}\n[원문 문단]:\n{target_rewrite_text}\n\n위 문단을 요청사항에 맞게 웹소설 프로 작가 수준으로 윤문해줘."
                        st.session_state.rewritten_result = generate_ai(p)
                        st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")
            else:
                st.warning("수정할 문단을 입력해 주세요.")
                
        if "rewritten_result" in st.session_state and st.session_state.rewritten_result:
            st.text_area("✨ 윤문된 결과", value=st.session_state.rewritten_result, height=200)
            if st.button("📥 이 윤문 결과를 5번 탭 본문으로 덮어쓰기"):
                st.session_state.current_ep_content = st.session_state.rewritten_result
                save_all_data()
                st.success("5번 탭 본문으로 적용되었습니다!")

    with st.expander("🪢 6. 복선(떡밥) & 미회수 단서 트래커", expanded=False):
        st.markdown("회차들에서 뿌려진 떡밥을 추출하고 회수 상태를 관리합니다.")
        target_foreshadow_scope = st.radio("떡밥 추출 대상 범위", ["서재의 전체 회차 종합 분석", "선택한 특정 본문만 분석"], horizontal=True)
        target_foreshadow_text = ""
        if target_foreshadow_scope == "서재의 전체 회차 종합 분석":
            target_foreshadow_text = "\n\n".join([f"<{k}>\n{v}" for k, v in st.session_state.episode_list.items()])
        else:
            target_foreshadow_text = select_target_text("foreshadow")
            
        if st.button("🔍 떡밥 및 복선 자동 추출/정리"):
            if target_foreshadow_text.strip():
                with st.spinner("본문에서 복선을 수집 및 분석 중입니다..."):
                    try:
                        p = f"[분석 대상 본문]\n{target_foreshadow_text}\n\n위 본문들에 등장한 핵심 단서, 의문의 인물, 미해결 사건 등 작가가 회수해야 할 '복선/떡밥 목록'을 번호 매겨 체계적으로 정리해줘."
                        st.session_state.foreshadowing_list = generate_ai(p)
                        save_all_data()
                        st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")
            else:
                st.warning("분석할 본문이 없습니다.")
        
        val_foreshadow = st.text_area(
            "📌 추적 중인 복선 및 떡밥 목록 (수정 가능 - 자동 저장됨)", 
            value=st.session_state.foreshadowing_list, 
            placeholder="예:\n- [미회수] 1화: 판게아 금고 열쇠의 행방",
            height=180,
            key="input_foreshadow"
        )
        if val_foreshadow != st.session_state.foreshadowing_list:
            st.session_state.foreshadowing_list = val_foreshadow
            save_all_data()

    with st.expander("🎭 7. 1인칭 주인공 / 관찰자 시점(POV) 전환기", expanded=False):
        st.markdown("선택한 본문이나 장면을 다른 인물의 시점으로 다시 씁니다.")
        target_pov_text = select_target_text("pov")
        
        pov_target = st.selectbox("변환할 시점", [
            "주인공 1인칭 시점 (내면 심리 극대화)",
            "조력자/추적자 시점에서 바라본 주인공 (3인칭 관찰자)",
            "빌런/상대방 시점 (이면의 음모와 긴장감)",
            "전지적 작가 시점 (객관적/웅장한 묘사)"
        ])
        
        if st.button("🎭 선택한 시점으로 본문 변환 실행"):
            if target_pov_text.strip():
                with st.spinner("시점을 전환하여 재집필 중입니다..."):
                    try:
                        p = f"[원문 본문]:\n{target_pov_text}\n\n[요청]: 위 장면을 '{pov_target}'으로 재해석하여 새로운 시각의 본문으로 다시 작성해줘."
                        st.session_state.pov_result_text = generate_ai(p)
                        st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")
            else:
                st.warning("변환할 본문 내용이 없습니다.")

        if "pov_result_text" in st.session_state and st.session_state.pov_result_text:
            st.text_area("🎭 시점 변환 본문 결과", value=st.session_state.pov_result_text, height=250)
            if st.button("📥 이 시점 변환 결과를 5번 탭 본문(현재 작업)으로 가져오기"):
                st.session_state.current_ep_content = st.session_state.pov_result_text
                save_all_data()
                st.success("5번 탭 본문으로 성공적으로 가져왔습니다!")

    with st.expander("🧠 8. 전체 회차 스마트 3줄 압축기 (Long-term Memory Compressor)", expanded=False):
        st.markdown("회차가 많아질 때 각 화의 핵심 사건을 3줄로 자동 압축하여 AI의 장기 기억 저장소에 보관합니다.")
        
        if st.button("🧠 서재 전체 회차 3줄 핵심 요약 압축 실행"):
            if st.session_state.episode_list:
                with st.spinner("전체 회차를 핵심 맥락으로 압축 중입니다..."):
                    try:
                        ep_combined = "\n\n".join([f"<{k}>\n{v}" for k, v in st.session_state.episode_list.items()])
                        p = f"[소설 전체 회차 본문]\n{ep_combined}\n\n각 회차별로 다음 3가지 핵심만 1줄씩, 총 3줄로 간결하게 요약 정리해줘:\n- 1) 발생한 핵심 사건\n- 2) 인물 관계 변화\n- 3) 새로 발생/회수된 복선"
                        st.session_state.compressed_summaries = generate_ai(p)
                        save_all_data()
                        st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")
            else:
                st.info("서재에 저장된 회차가 없습니다.")
                
        val_comp = st.text_area(
            "📌 전체 회차 압축 줄거리 (자동 저장됨)", 
            value=st.session_state.compressed_summaries, 
            height=200,
            key="input_comp"
        )
        if val_comp != st.session_state.compressed_summaries:
            st.session_state.compressed_summaries = val_comp
            save_all_data()
