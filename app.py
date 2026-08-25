import streamlit as st
import json
import os
from google import genai
from google.genai import types

st.set_page_config(page_title="웹소설 스튜디오 Pro Max", layout="wide")

# ==========================================
# 0. 영구 자동 저장 데이터 파일 시스템
# ==========================================
DATA_FILE = "novel_project_data.json"

default_data = {
    "custom_story_lore": "",
    "worldview": "",
    "synopsis": "",
    "custom_char_lore": "",
    "characters": "",
    "plot": "",
    "ep_treatment_guideline": "",
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

if "initialized" not in st.session_state:
    saved_state = load_saved_data()
    for k, v in saved_state.items():
        st.session_state[k] = v
    st.session_state.initialized = True

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
        ["19세 성인/하드보일드 (적나라한 심리/폭력/어두운 묘사 허용)", "노필터 다크 판타지/스릴러", "15세 이용가 (긴장감/현실적 묘사)", "전체이용가 (대중적/순화)"]
    )
    detail_style = st.selectbox(
        "문체 및 묘사 디테일",
        ["극적 심리/감각적 고밀도 묘사", "클리프행어/도파민 극대화", "속도감 중심 (대화/사건 위주)", "균형 잡힌 웹소설 표준"]
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

# 메인 화면
st.title("✍️ 웹소설 유니버스 & 스튜디오 Pro Max")
st.caption("🔒 모든 고유 설정, 인물 원안, 회차 본문은 입력 즉시 영구 자동 저장됩니다.")

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
- 작가의 지시와 제공된 시작 초안을 100% 최우선으로 준수하여 스토리를 이어나갈 것.
- 뻔한 날씨 묘사(비/장대비 등)나 진부한 클리셰 도입부를 절대 독자적으로 창작하지 말 것.
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

def build_context_prompt(use_story=True, use_wv=False, use_char_lore=True, use_chars=False, use_synop=False, use_plot=False, use_treatment=False, use_selected_eps=True, use_foreshadow=False, use_compressed=False):
    ctx = []
    if use_story and st.session_state.custom_story_lore.strip():
        ctx.append(f"[작가 고유 스토리/세계관 원안]\n{st.session_state.custom_story_lore}")
    if use_wv and st.session_state.worldview.strip():
        ctx.append(f"[확장 세계관]\n{st.session_state.worldview}")
    if use_char_lore and st.session_state.custom_char_lore.strip():
        ctx.append(f"[작가 고유 캐릭터 원안]\n{st.session_state.custom_char_lore}")
    if use_chars and st.session_state.characters.strip():
        ctx.append(f"[등장인물 상세 설정집]\n{st.session_state.characters}")
    if use_synop and st.session_state.synopsis.strip():
        ctx.append(f"[기존 시놉시스 맥락]\n{st.session_state.synopsis}")
    if use_plot and st.session_state.plot.strip():
        ctx.append(f"[플롯 및 트리트먼트]\n{st.session_state.plot}")
    if use_treatment and st.session_state.ep_treatment_guideline.strip():
        ctx.append(f"[★ 이번 회차 전용 참고 시나리오 & 씬 트리트먼트 콘티]\n{st.session_state.ep_treatment_guideline}")
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
        height=230,
        key="input_custom_story"
    )
    if val_story != st.session_state.custom_story_lore:
        st.session_state.custom_story_lore = val_story
        save_all_data()

    st.markdown("---")
    st.subheader("🌍 1-2. 세계관/스토리 창작 및 확장 엔진")
    
    wv_gen_mode = st.radio("창작 모드 선택", ["🎯 특정 세부 설정만 집중 창작 (부분 설정)", "🌐 전체 세계관 종합 확장"], horizontal=True, key="wv_gen_mode")
    
    if wv_gen_mode == "🎯 특정 세부 설정만 집중 창작 (부분 설정)":
        target_wv_topic = st.text_input("💡 집중 창작할 세부 주제", placeholder="예: 판게아 금고의 보안 규칙, 지혜원의 설립 배경, 암흑가 달란트 환전 시스템", key="target_wv_topic")
        wv_detail_req = st.text_area("보완/지시 요구사항", placeholder="예: 쉽게 뚫리지 않는 치밀한 제약 조건을 넣고, 어두운 비밀이 얽혀있게 만들어줘.", key="wv_detail_req", height=80)
        wv_prompt_main = f"""[★ 특정 세부 설정 집중 창작 요청]
주제: "{target_wv_topic}"
세부 지시: "{wv_detail_req}"
위 특정 주제에 대해 개연성 있고 디테일한 설정을 깊이 있게 창작해줘. 뻔한 설정을 지양하고 서사의 긴장감을 높일 수 있는 구체적인 규칙과 숨겨진 이면을 작성할 것."""
    else:
        col1, col2 = st.columns(2)
        with col1:
            genre = st.selectbox("장르", ["판타지", "현대판타지", "무협", "로맨스판타지", "SF", "미스터리/스릴러", "다크판타지", "기타"], key="wv_genre")
            tone = st.text_input("분위기/톤앤매너", placeholder="예: 하드보일드, 긴장감 넘치는 추적", key="wv_tone")
        with col2:
            concept = st.text_area("보완할 키워드/테마", placeholder="예: 세력 간 암투, 고유 능력의 한계", key="wv_concept", height=90)
        wv_prompt_main = f"""[전체 세계관 종합 확장]
장르: {genre} / 톤: {tone} / 키워드: {concept}
세부 사회구조, 세력도, 인물 간 권력 관계, 세계관의 절대 규칙을 풍성하게 확장해줘."""

    use_story_for_wv = st.checkbox("🔗 [접근 제어] 고유 스토리 원안을 기반으로 창작", value=True, key="acc_wv_story")
    
    if st.button("🌍 세계관/설정 생성 실행", key="btn_gen_wv"):
        with st.spinner("설정을 정밀 구축 중입니다..."):
            try:
                base_ctx = f"[작가의 고유 스토리 설정]\n{st.session_state.custom_story_lore}\n\n" if use_story_for_wv else ""
                p = f"{base_ctx}\n{wv_prompt_main}"
                st.session_state.worldview = generate_ai(p)
                save_all_data()
                st.rerun()
            except Exception as e:
                st.error(f"오류: {e}")

    val_wv = st.text_area("생성/확장된 설정 결과", value=st.session_state.worldview, height=220, key="input_wv")
    if val_wv != st.session_state.worldview:
        st.session_state.worldview = val_wv
        save_all_data()

    st.markdown("#### 🎯 생성된 내용 중 일부만 내 원안(1-1)에 반영하기")
    c_filter, c_btn = st.columns([3, 1])
    with c_filter:
        wv_apply_target = st.text_input("원안에 반영할 특정 항목/내용 입력", placeholder="예: 판게아 금고의 작동 규칙만 반영, 지혜원 비밀 반영", key="wv_apply_target")
    with c_btn:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if st.button("📥 스토리 원안에 선택 반영", key="btn_apply_wv_part"):
            if not st.session_state.worldview.strip():
                st.warning("먼저 설정을 생성하거나 결과란에 내용이 있어야 합니다.")
            elif wv_apply_target.strip():
                with st.spinner("해당 항목을 추출하여 원안에 병합 중입니다..."):
                    try:
                        extract_p = f"""[생성된 설정 전문]:\n{st.session_state.worldview}\n\n[추출 및 정돈 요청]:\n위 내용 중에서 '{wv_apply_target}'에 해당하는 핵심 내용만 깔끔한 요약 포인트 형태로 뽑아줘."""
                        extracted_part = generate_ai(extract_p)
                        
                        st.session_state.custom_story_lore += f"\n\n[추가 반영 설정 - {wv_apply_target}]\n{extracted_part}"
                        save_all_data()
                        st.success(f"'{wv_apply_target}' 내용이 1-1 고유 스토리 원안에 성공적으로 추가되었습니다!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"추출 오류: {e}")
            else:
                st.warning("반영할 내용을 입력해 주세요.")

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
        height=230,
        key="input_custom_char"
    )
    if val_char != st.session_state.custom_char_lore:
        st.session_state.custom_char_lore = val_char
        save_all_data()

    st.markdown("---")
    st.subheader("👥 2-2. 인물 프로필 및 세부 비하인드 창작 엔진")
    
    char_gen_mode = st.radio("인물 창작 모드 선택", ["🎯 특정 인물의 세부 비하인드/동기만 창작 (예: 경찰이 된 이유)", "👥 전체 인물 프로필 일괄 상세화"], horizontal=True, key="char_gen_mode")
    
    if char_gen_mode == "🎯 특정 인물의 세부 비하인드/동기만 창작 (예: 경찰이 된 이유)":
        target_char_focus = st.text_input("💡 대상 인물 & 창작할 주제", placeholder="예: 백은조가 경찰(실종수사관)이 된 결정적 이유, 추수국의 왼쪽 뺨 흉터의 비밀", key="target_char_focus")
        char_focus_req = st.text_area("세부 요구사항", placeholder="예: 과거 지혜원 사건과 얽힌 비극적인 가족사 연결, 냉철한 성격이 형성된 계기 포함", key="char_focus_req", height=80)
        char_prompt_main = f"""[★ 특정 인물 세부 설정/비하인드 집중 창작]
대상 및 주제: "{target_char_focus}"
세부 지시: "{char_focus_req}"
위 인물의 해당 주제에 대해 평면적인 설정을 넘어선 강렬한 서사와 감정적 결핍, 입체적인 비하인드 스토리를 창작해줘."""
    else:
        char_desc = st.text_area("⚡ 추가/보완 요청 사항", placeholder="예: 백은조는 여자야. 20대 중반의 엄청난 미녀. 그리고 추수국 설정 보완해줘.", key="char_expand_req", height=80)
        char_prompt_main = f"""[전체 등장인물 상세 프로필 설계]
요청사항: "{char_desc if char_desc.strip() else '기본 설정 상세화'}"
주요 인물들의 외모, 성격, 심리적 결핍, 능력치 한계, 대표 대사 톤을 완성해줘."""

    c1, c2, c3 = st.columns(3)
    with c1:
        use_char_lore_for_c = st.checkbox("🔗 고유 캐릭터 원안 반영", value=True, key="acc_c_char")
    with c2:
        use_story_for_c = st.checkbox("🔗 고유 스토리 설정 반영", value=True, key="acc_c_story")
    with c3:
        use_wv_for_c = st.checkbox("🔗 확장 세계관 반영", value=True, key="acc_c_wv")

    if st.button("👥 캐릭터 설정 생성 실행", key="btn_gen_char"):
        with st.spinner("캐릭터 세부 서사를 설계 중입니다..."):
            try:
                ctx = build_context_prompt(
                    use_story=use_story_for_c, 
                    use_wv=use_wv_for_c, 
                    use_char_lore=use_char_lore_for_c, 
                    use_chars=False, use_synop=False, use_plot=False, use_treatment=False, use_selected_eps=False, use_foreshadow=False, use_compressed=False
                )
                p = f"""[배경 설정]\n{ctx}\n\n{char_prompt_main}"""
                
                st.session_state.characters = generate_ai(p)
                save_all_data()
                st.rerun()
            except Exception as e:
                st.error(f"오류: {e}")

    val_chars = st.text_area("생성된 인물 설정 결과", value=st.session_state.characters, height=220, key="input_chars")
    if val_chars != st.session_state.characters:
        st.session_state.characters = val_chars
        save_all_data()

    st.markdown("#### 🎯 생성된 인물 설정 중 특정 내용만 캐릭터 원안(2-1)에 반영하기")
    c_cfilter, c_cbtn = st.columns([3, 1])
    with c_cfilter:
        char_apply_target = st.text_input("원안에 반영할 특정 인물/설정 입력", placeholder="예: 백은조가 경찰이 된 이유 반영, 추수국의 트라우마 반영", key="char_apply_target")
    with c_cbtn:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if st.button("📥 캐릭터 원안에 선택 반영", key="btn_apply_char_part"):
            if not st.session_state.characters.strip():
                st.warning("먼저 인물 설정을 생성하거나 결과란에 내용이 있어야 합니다.")
            elif char_apply_target.strip():
                with st.spinner("인물 설정을 추출하여 원안에 병합 중입니다..."):
                    try:
                        extract_cp = f"""[생성된 인물 설정 전문]:\n{st.session_state.characters}\n\n[추출 요청]:\n위 내용 중 '{char_apply_target}'에 해당하는 핵심 내용만 깔끔하게 요약 추출해줘."""
                        extracted_cpart = generate_ai(extract_cp)
                        
                        st.session_state.custom_char_lore += f"\n\n[추가 반영 설정 - {char_apply_target}]\n{extracted_cpart}"
                        save_all_data()
                        st.success(f"'{char_apply_target}' 내용이 2-1 캐릭터 원안에 성공적으로 추가되었습니다!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"추출 오류: {e}")
            else:
                st.warning("반영할 내용을 입력해 주세요.")

# 탭 3: 시놉시스
with tab3:
    st.subheader("🎲 3. 시놉시스 생성")
    
    synop_mode = st.radio("시놉시스 생성 범위", ["전체 메인 시놉시스 (작품 전체 윤곽)", "특정 회차 전용 시놉시스 (예: 제1화 단독 줄거리)"], horizontal=True, key="syn_scope_radio")
    
    if synop_mode == "특정 회차 전용 시놉시스 (예: 제1화 단독 줄거리)":
        target_ep_name = st.text_input("목표 회차", value="제1화", placeholder="예: 제1화, 제2화 등", key="syn_ep_target")
        synop_keyword = st.text_area("⚡ 해당 회차 핵심 사건 및 전개 키워드 (★최우선 반영)", placeholder="예: 나이 어린 추수국이 지혜원에서 소원빌다 능력을 얻고 빚을 지는 이야기", key="syn_keyword_ep", height=85)
    else:
        target_ep_name = "전체 메인"
        synop_keyword = st.text_area("⚡ 메인 시놉시스 핵심 사건 및 전개 키워드 (★최우선 반영)", placeholder="예: 거액의 달란트를 노리는 암투, 프리텐더 연합군 집결", key="syn_keyword_main", height=85)

    st.markdown("**접근 여부 설정 (프롬프트 반영 항목)**")
    sc1, sc2, sc3, sc4, sc5 = st.columns(5)
    with sc1:
        use_s_story = st.checkbox("고유 스토리 원안", value=True, key="syn_story")
    with sc2:
        use_s_wv = st.checkbox("확장 세계관", value=False, key="syn_wv")
    with sc3:
        use_s_char_lore = st.checkbox("캐릭터 원안", value=True, key="syn_char_lore")
    with sc4:
        use_s_chars = st.checkbox("상세 인물집", value=False, key="syn_chars")
    with sc5:
        use_s_eps = st.checkbox("체크된 회차 글", value=(synop_mode != "전체 메인 시놉시스 (작품 전체 윤곽)"), key="syn_eps")

    if st.button("🎲 시놉시스 주사위 굴리기 (즉시 생성)", key="btn_gen_synopsis"):
        with st.spinner("작가의 핵심 키워드를 최우선으로 분석하여 시놉시스를 생성 중입니다..."):
            try:
                ctx = build_context_prompt(
                    use_story=use_s_story, 
                    use_wv=use_s_wv, 
                    use_char_lore=use_s_char_lore, 
                    use_chars=use_s_chars, 
                    use_synop=False, use_plot=False,
                    use_treatment=False,
                    use_selected_eps=use_s_eps,
                    use_foreshadow=True,
                    use_compressed=True
                )
                
                if synop_mode == "특정 회차 전용 시놉시스 (예: 제1화 단독 줄거리)":
                    p = f"""[★ 절대 규칙: {target_ep_name} 단독 회차 시놉시스만 작성할 것]
- 경고: 작품 전체 기획서나 메인 시놉시스를 절대 작성하지 마십시오.
- 이번 요청은 오직 **[{target_ep_name}] 1화 안에서 일어나는 단독 줄거리**입니다.
- 작가의 지시 키워드: "{synop_keyword if synop_keyword.strip() else '1화 시작 줄거리'}"

[참조 배경 설정]
{ctx}

[출력 양식]
# [{target_ep_name} 단독 시놉시스]
- **회차 목표/테마**: 
- **등장인물 및 무대**: 
- **1단계 (도입/발단)**: (작가의 키워드 사건 시작)
- **2단계 (전개/사건 발생)**: (구체적 갈등 및 능력 발현/사건 전개)
- **3단계 (위기/절정)**: (대가 지불, 빚, 위기 상황 발생)
- **4단계 (결말 및 훅)**: (다음 회차로 연결되는 엔딩)"""
                else:
                    p = f"""[★ 메인 시놉시스 작성 지침]
작가의 핵심 키워드: "{synop_keyword if synop_keyword.strip() else '작품 전체 메인 전개'}"

[참조 배경 설정]
{ctx}

[출력 양식]
# [작품 전체 메인 시놉시스]
작품 전체의 기획 의도, 메인 로그라인, 기승전결 서사 구조를 작성할 것."""

                result_syn = generate_ai(p)
                st.session_state.synopsis = result_syn
                save_all_data()
                st.rerun()
            except Exception as e:
                st.error(f"시놉시스 생성 오류: {e}")

    val_syn = st.text_area("🎲 생성된 시놉시스 결과 (수정 및 자동 저장됨)", value=st.session_state.synopsis, height=280, key="input_syn")
    if val_syn != st.session_state.synopsis:
        st.session_state.synopsis = val_syn
        save_all_data()

    if st.session_state.synopsis.strip():
        st.markdown("#### 🎯 시놉시스 내용 중 일부만 내 원안(1-1)에 반영하기")
        c_sfilter, c_sbtn = st.columns([3, 1])
        with c_sfilter:
            syn_apply_target = st.text_input("원안에 반영할 특정 사건/전개 입력", placeholder="예: 추수국이 빚을 지게 되는 세부 계약 내용만 반영", key="syn_apply_target")
        with c_sbtn:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            if st.button("📥 스토리 원안에 선택 반영", key="btn_apply_syn_part"):
                if syn_apply_target.strip():
                    with st.spinner("시놉시스 핵심 사건을 원안에 병합 중입니다..."):
                        try:
                            extract_sp = f"""[시놉시스 전문]:\n{st.session_state.synopsis}\n\n[추출 요청]:\n위 내용 중 '{syn_apply_target}'에 해당하는 핵심 사건만 깔끔하게 요약 추출해줘."""
                            extracted_spart = generate_ai(extract_sp)
                            
                            st.session_state.custom_story_lore += f"\n\n[추가 반영 사건 - {syn_apply_target}]\n{extracted_spart}"
                            save_all_data()
                            st.success(f"'{syn_apply_target}' 내용이 1-1 고유 스토리 원안에 성공적으로 추가되었습니다!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"추출 오류: {e}")
                else:
                    st.warning("반영할 내용을 입력해 주세요.")

# 탭 4: 플롯
with tab4:
    st.subheader("🗺️ 4. 회차별 플롯 & 트리트먼트")
    
    plot_mode = st.radio("플롯 설계 범위", ["특정 회차 전용 플롯 (예: 제1화 씬별 상세 전개)", "연속 회차/전체 플롯 흐름 (예: 1~5화 트리트먼트)"], horizontal=True)
    
    if plot_mode == "특정 회차 전용 플롯 (예: 제1화 씬별 상세 전개)":
        target_plot_ep = st.text_input("설계할 회차", value="제1화", placeholder="예: 제1화")
        plot_goal = st.text_area("⚡ 해당 회차 전개 목표 및 위기 (★최우선 반영)", placeholder="예: 흑막 크람푸스의 음모 포착 및 첫 격돌", key="plot_goal_input", height=85)
        plot_instruction = f"""[★ 최우선 필수 지침 (Override Rule)]
작가의 전개 목표: "{plot_goal if plot_goal.strip() else '회차 전개'}"
위 목표를 바탕으로 '{target_plot_ep}'의 [오프닝 씬 -> 갈등 심화 -> 절체절명 위기 -> 엔딩 클리프행어]를 씬 단위로 정밀하게 설계해줘."""
    else:
        plot_goal = st.text_area("⚡ 플롯 전개 범위 및 핵심 흐름 (★최우선 반영)", placeholder="예: 1~4단계 역전의 판게아 정상 결전 흐름", key="plot_goal_main_input", height=85)
        plot_instruction = f"""[★ 최우선 필수 지침 (Override Rule)]
작가의 전개 범위: "{plot_goal if plot_goal.strip() else '전체 흐름'}"
회차별 핵심 사건과 떡밥 배치 구조를 단계별로 체계적으로 설계해줘."""

    st.markdown("**접근 여부 설정 (프롬프트 반영 항목)**")
    pc1, pc2, pc3, pc4, pc5, pc6 = st.columns(6)
    with pc1:
        use_p_story = st.checkbox("스토리 원안", value=True, key="plot_story")
    with pc2:
        use_p_wv = st.checkbox("세계관", value=False, key="plot_wv")
    with pc3:
        use_p_char = st.checkbox("캐릭터 원안", value=True, key="plot_char_lore")
    with pc4:
        use_p_chars = st.checkbox("상세 인물집", value=False, key="plot_chars")
    with pc5:
        use_p_syn = st.checkbox("시놉시스", value=False, key="plot_syn")
    with pc6:
        use_p_eps = st.checkbox("체크된 회차 글", value=True, key="plot_eps")

    if st.button("🗺️ 플롯 설계 생성 (즉시 생성)", key="btn_gen_plot"):
        with st.spinner("플롯을 정밀 구성 중입니다..."):
            try:
                ctx = build_context_prompt(
                    use_story=use_p_story, 
                    use_wv=use_p_wv, 
                    use_char_lore=use_p_char, 
                    use_chars=use_p_chars, 
                    use_synop=use_p_syn, 
                    use_plot=False,
                    use_treatment=False,
                    use_selected_eps=use_p_eps,
                    use_foreshadow=True,
                    use_compressed=True
                )
                p = f"{ctx}\n\n{plot_instruction}"
                st.session_state.plot = generate_ai(p)
                save_all_data()
                st.rerun()
            except Exception as e:
                st.error(f"플롯 생성 오류: {e}")

    val_plot = st.text_area("회차별 플롯/트리트먼트 결과", value=st.session_state.plot, height=280, key="input_plot")
    if val_plot != st.session_state.plot:
        st.session_state.plot = val_plot
        save_all_data()

# 탭 5: 본문 집필 (초안 직접 이어쓰기 엔진 탑재)
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

    st.markdown("📝 **이번 회차에 참고할 핵심 시나리오 & 씬 트리트먼트 콘티 (★최우선 반영)**")
    val_treatment = st.text_area(
        "이번 화에서 일어날 구체적인 장면, 대사, 초안을 여기에 적으세요. AI가 이 텍스트를 시작점으로 삼아 곧바로 뒷이야기를 이어서 작성합니다.",
        value=st.session_state.ep_treatment_guideline,
        placeholder="예:\n나이 어린 추수국이 크리스마스 이브 지혜원에서 소원을 빌다 루돌프의 눈 능력을 얻고 1조의 빚을 지게 되는 장면.",
        height=140,
        key="input_treatment"
    )
    if val_treatment != st.session_state.ep_treatment_guideline:
        st.session_state.ep_treatment_guideline = val_treatment
        save_all_data()

    st.markdown("**접근 여부 설정 (프롬프트 반영 항목)**")
    ec1, ec2, ec3, ec4 = st.columns(4)
    with ec1:
        use_e_story = st.checkbox("고유 스토리 원안", value=True, key="ep_story")
    with ec2:
        use_e_char = st.checkbox("고유 캐릭터 원안", value=True, key="ep_char_lore")
    with ec3:
        use_e_treat = st.checkbox("위 콘티/초안 (최우선)", value=True, key="ep_treat")
    with ec4:
        use_e_eps = st.checkbox("체크된 이전 회차 본문", value=False, key="ep_eps")

    col_gen, col_save = st.columns([1, 1])
    with col_gen:
        if st.button("📖 AI 본문 초안 작성 (콘티 직접 이어쓰기)", key="btn_gen_ep_content"):
            with st.spinner("작가의 초안을 바탕으로 곧바로 뒷이야기를 집필 중입니다..."):
                try:
                    user_starter_draft = st.session_state.ep_treatment_guideline.strip()
                    
                    ctx = build_context_prompt(
                        use_story=use_e_story, 
                        use_wv=False, 
                        use_char_lore=use_e_char, 
                        use_chars=False, 
                        use_synop=False, 
                        use_plot=False,
                        use_treatment=False,
                        use_selected_eps=use_e_eps,
                        use_foreshadow=False,
                        use_compressed=False
                    )
                    
                    p = f"""[★ 절대 규칙: 작가의 초안 직접 이어쓰기 지침 (Override Rule)]
1. 작가가 아래 [작가가 직접 작성한 시작 초안]을 제공했습니다.
2. 엉뚱한 날씨 묘사(예: 비가 내렸다 등)나 다른 성인 시점의 오프닝을 새로 만들지 마십시오.
3. 작가의 시작 초안 상황과 톤을 그대로 이어받아, 소설의 다음 장면(지혜원에서 소원을 빌고, 능력을 얻고, 1조의 빚을 지게 되는 충격적인 전개)을 곧바로 이어서 완성하세요.

[작가가 직접 작성한 시작 초안]:
\"\"\"
{user_starter_draft if user_starter_draft else '1화 시작 초안'}
\"\"\"

[참조용 기본 배경 설정]
{ctx}

[집필 회차]: {st.session_state.current_ep_title}
위 시작 초안의 뒷부분부터 완결감 있게 이어지는 웹소설 1화 분량의 본문을 완성해줘."""

                    ai_continuation = generate_ai(p)
                    
                    # 작가의 초안이 시작 부분에 누락되지 않도록 결합 보정
                    if user_starter_draft and not ai_continuation.strip().startswith(user_starter_draft[:20]):
                        full_content = f"{user_starter_draft}\n\n{ai_continuation}"
                    else:
                        full_content = ai_continuation
                        
                    st.session_state.current_ep_content = full_content
                    st.session_state.episode_list[st.session_state.current_ep_title] = full_content
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
                        ctx = build_context_prompt(use_story=True, use_wv=False, use_char_lore=True, use_chars=False, use_synop=False, use_plot=False, use_treatment=False, use_selected_eps=True, use_foreshadow=True, use_compressed=True)
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
                        ctx = build_context_prompt(use_story=False, use_wv=False, use_char_lore=True, use_chars=False, use_synop=False, use_plot=False, use_treatment=False, use_selected_eps=False)
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
