import streamlit as st
import json
import os
from google import genai
from google.genai import types

st.set_page_config(page_title="웹소설 스튜디오 Pro Max", layout="wide")

# ==========================================
# 0. 영구 저장 데이터 파일 시스템
# ==========================================
DATA_FILE = "novel_project_data.json"

default_data = {
    "custom_story_lore": "",
    "worldview": "",
    "custom_char_lore": "",
    "characters": "",
    "ep_treatment_dict": {
        "제1화": "크리스마스 이브 지혜원에서 추수국이 소원을 빌고 루돌프의 눈을 얻으며 1조의 빚을 짐."
    },
    "current_treatment_ep": "제1화",
    "synopsis": "",
    "plot": "",
    "ep_treatment_guideline": "",
    "notes": "",
    "foreshadowing_list": "",
    "compressed_summaries": "",
    "episode_list": {},
    "selected_episodes": [],
    "current_ep_title": "제1화",
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
    
    creativity = st.slider("AI 창의성 / 자유도 (Temperature)", min_value=0.0, max_value=2.0, value=1.1, step=0.1)
    rating_level = st.selectbox(
        "표현 수위 / 연령 등급",
        ["19세 성인/하드보일드 (적나라한 심리/폭력/어두운 묘사 허용)", "노필터 다크 판타지/스릴러", "15세 이용가 (긴장감/현실적 묘사)", "전체이용가 (대중적/순화)"]
    )
    detail_style = st.selectbox(
        "문체 및 묘사 디테일",
        ["극적 심리/감각적 고밀도 묘사", "클리프행어/도파민 극대화", "속도감 중심 (대화/사건 위주)", "균형 잡힌 웹소설 표준"]
    )
    target_length = st.select_slider(
        "초안 생성 분량 목표",
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
st.caption("🔒 모든 데이터는 각 탭의 [💾 저장] 버튼을 누를 때 안전하게 영구 저장됩니다.")

if not api_key:
    st.warning("👈 좌측 상단 화살표(>>)를 눌러 사이드바에 Gemini API Key를 입력해 주세요.")
    st.stop()

client = genai.Client(api_key=api_key)
MODEL_NAME = "gemini-3.6-flash"

system_prompt_addon = f"""
[절대 준수 3중 집필 헌법]
1. [3단계: 이번 화 현장 콘티 & 시작 오프닝 초안]을 최상위 명령으로 100% 반영한다.
2. [2단계: 연결된 회차별 트리트먼트]의 사건 진행 뼈대를 절대 이탈하지 않는다.
3. [1단계: 고유 원안]의 인물 설정과 세계관을 바탕으로 살을 붙인다.
4. 시작 오프닝 초안이 주어지면, 그 상황과 대사에서 1초도 건너뛰지 말고 곧바로 이어지는 뒷장면을 작성할 것.
5. 진부한 날씨 묘사(비, 장대비 등)로 시작하는 클리셰를 절대 생성하지 않는다.
6. 표현 수위: {rating_level} | 문체: {detail_style} | 분량: {target_length}
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
    "🗺️ 3. 회차별 트리트먼트 연동",
    "🎲 4. 시나리오 주사위 (전개 발산)", 
    "📖 5. 3중 본문 집필 & 서재 저장",
    "🛠️ 6. 작가 전문 집필 도구 (고급 엔진)"
])

# 탭 1: 스토리 설정
with tab1:
    st.subheader("📌 1-1. 내가 만든 고유 스토리/세계관 설정")
    
    with st.expander("📥 텍스트 직접 붙여넣기로 원안 업데이트 (복붙 퀵 패치)", expanded=False):
        paste_story_text = st.text_area("외부에서 복사한 설정 텍스트 붙여넣기", placeholder="외부 제미나이 등에서 정리한 세계관/스토리 설정을 여기에 붙여넣으세요.", height=130, key="paste_story_box")
        c_p1, c_p2 = st.columns(2)
        with c_p1:
            if st.button("📝 원안에 [덮어쓰기] (기존 내용 교체)", key="btn_overwrite_story"):
                if paste_story_text.strip():
                    st.session_state.custom_story_lore = paste_story_text.strip()
                    save_all_data()
                    st.success("스토리 원안에 덮어썼습니다!")
                    st.rerun()
                else:
                    st.warning("붙여넣을 텍스트가 없습니다.")
        with c_p2:
            if st.button("➕ 기존 원안 뒤에 [추가하기] (이어붙이기)", key="btn_append_story"):
                if paste_story_text.strip():
                    if st.session_state.custom_story_lore.strip():
                        st.session_state.custom_story_lore += f"\n\n{paste_story_text.strip()}"
                    else:
                        st.session_state.custom_story_lore = paste_story_text.strip()
                    save_all_data()
                    st.success("기존 원안 뒤에 내용을 추가했습니다!")
                    st.rerun()
                else:
                    st.warning("추가할 텍스트가 없습니다.")

    txt_story = st.file_uploader("스토리 설정 파일(.txt) 불러오기", type=["txt"], key="txt_story")
    if txt_story is not None:
        try:
            st.session_state.custom_story_lore = txt_story.read().decode("utf-8")
            save_all_data()
            st.success("스토리 설정을 불러왔습니다!")
        except Exception as e:
            st.error(f"파일 읽기 오류: {e}")
            
    st.text_area(
        "작가 고유 스토리/배경 원안", 
        value=st.session_state.custom_story_lore, 
        placeholder="예: 사건의 배경, 범죄 조직의 실체, 고유 규칙, 미스터리 등",
        height=230,
        key="custom_story_lore"
    )
    if st.button("💾 스토리 원안 저장", key="btn_save_story_lore"):
        save_all_data()
        st.success("스토리 원안이 안전하게 저장되었습니다!")

    st.markdown("---")
    st.subheader("🌍 1-2. 세계관/스토리 창작 및 확장 엔진")
    
    wv_gen_mode = st.radio("창작 모드 선택", ["🎯 특정 세부 설정만 집중 창작 (부분 설정)", "🌐 전체 세계관 종합 확장"], horizontal=True, key="wv_gen_mode")
    
    if wv_gen_mode == "🎯 특정 세부 설정만 집중 창작 (부분 설정)":
        target_wv_topic = st.text_input("💡 집중 창작할 세부 주제", placeholder="예: 판게아 금고의 보안 규칙, 지혜원의 설립 배경, 암흑가 달란트 환전 시스템", key="target_wv_topic")
        wv_detail_req = st.text_area("보완/지시 요구사항", placeholder="예: 쉽게 뚫리지 않는 치밀한 제약 조건을 넣고, 어두운 비밀이 얽혀있게 만들어줘.", key="wv_detail_req", height=80)
        wv_prompt_main = f"""[★ 특정 세부 설정 집중 창작 요청]
주제: "{target_wv_topic}"
세부 지시: "{wv_detail_req}"
위 특정 주제에 대해 개연성 있고 디테일한 설정을 깊이 있게 창작해줘."""
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

    st.text_area("생성/확장된 설정 결과", value=st.session_state.worldview, height=220, key="worldview")
    if st.button("💾 확장 세계관 결과 저장", key="btn_save_wv"):
        save_all_data()
        st.success("확장 세계관 결과가 저장되었습니다!")

# 탭 2: 인물 설정
with tab2:
    st.subheader("📌 2-1. 내가 만든 고유 캐릭터 원안")
    
    with st.expander("📥 텍스트 직접 붙여넣기로 원안 업데이트 (복붙 퀵 패치)", expanded=False):
        paste_char_text = st.text_area("외부에서 복사한 인물 설정 텍스트 붙여넣기", placeholder="외부 제미나이 등에서 정리한 캐릭터 프로필을 여기에 붙여넣으세요.", height=130, key="paste_char_box")
        c_cp1, c_cp2 = st.columns(2)
        with c_cp1:
            if st.button("📝 원안에 [덮어쓰기] (기존 인물 교체)", key="btn_overwrite_char"):
                if paste_char_text.strip():
                    st.session_state.custom_char_lore = paste_char_text.strip()
                    save_all_data()
                    st.success("캐릭터 원안에 덮어썼습니다!")
                    st.rerun()
                else:
                    st.warning("붙여넣을 텍스트가 없습니다.")
        with c_cp2:
            if st.button("➕ 기존 원안 뒤에 [추가하기] (새 인물/설정 덧붙이기)", key="btn_append_char"):
                if paste_char_text.strip():
                    if st.session_state.custom_char_lore.strip():
                        st.session_state.custom_char_lore += f"\n\n{paste_char_text.strip()}"
                    else:
                        st.session_state.custom_char_lore = paste_char_text.strip()
                    save_all_data()
                    st.success("기존 원안 뒤에 인물 설정을 추가했습니다!")
                    st.rerun()
                else:
                    st.warning("추가할 텍스트가 없습니다.")

    txt_char = st.file_uploader("인물 설정 파일(.txt) 불러오기", type=["txt"], key="txt_char")
    if txt_char is not None:
        try:
            st.session_state.custom_char_lore = txt_char.read().decode("utf-8")
            save_all_data()
            st.success("인물 설정을 불러왔습니다!")
        except Exception as e:
            st.error(f"파일 읽기 오류: {e}")
            
    st.text_area(
        "작가 고유 인물 원안 (주인공, 조력자, 핵심 빌런)", 
        value=st.session_state.custom_char_lore, 
        placeholder="예:\n- 주인공: 백은조, 추수국\n- 빌런: 크람푸스",
        height=230,
        key="custom_char_lore"
    )
    if st.button("💾 캐릭터 원안 저장", key="btn_save_char_lore"):
        save_all_data()
        st.success("캐릭터 원안이 안전하게 저장되었습니다!")

    st.markdown("---")
    st.subheader("👥 2-2. 인물 프로필 및 세부 비하인드 창작 엔진")
    
    char_desc = st.text_area("⚡ 캐릭터 상세화/추가 요청 사항", placeholder="예: 백은조와 추수국의 과거 인연과 결핍을 보완해줘.", key="char_expand_req", height=80)
    if st.button("👥 캐릭터 설정 생성 실행", key="btn_gen_char"):
        with st.spinner("캐릭터 세부 서사를 설계 중입니다..."):
            try:
                ctx = build_context_prompt(use_story=True, use_wv=False, use_char_lore=True, use_chars=False, use_synop=False, use_plot=False, use_treatment=False, use_selected_eps=False)
                p = f"""[배경 설정]\n{ctx}\n\n[등장인물 상세 프로필 설계]:\n{char_desc}"""
                st.session_state.characters = generate_ai(p)
                save_all_data()
                st.rerun()
            except Exception as e:
                st.error(f"오류: {e}")

    st.text_area("생성된 인물 설정 결과", value=st.session_state.characters, height=220, key="characters")
    if st.button("💾 인물 설정 상세 결과 저장", key="btn_save_chars"):
        save_all_data()
        st.success("인물 설정 상세 결과가 저장되었습니다!")

# 탭 3: 회차별 트리트먼트 연동 관리
with tab3:
    st.subheader("🗺️ 3. 회차별 고정 트리트먼트 관리 (1단계 사건 뼈대)")
    st.caption("각 회차를 선택하고, 해당 화의 핵심 사건 뼈대를 적어둔 뒤 [💾 저장] 버튼을 누르면 4번(시나리오), 5번(본문)에 연동됩니다.")
    
    col_ep_sel, col_ep_add = st.columns([3, 1])
    with col_ep_sel:
        current_t_ep = st.selectbox(
            "관리할 회차 선택", 
            options=list(st.session_state.ep_treatment_dict.keys()),
            key="treat_ep_selector"
        )
    with col_ep_add:
        new_ep_name = st.text_input("새 회차 추가", placeholder="예: 제2화", key="new_ep_treat_input")
        if st.button("➕ 회차 추가"):
            if new_ep_name.strip() and new_ep_name not in st.session_state.ep_treatment_dict:
                st.session_state.ep_treatment_dict[new_ep_name.strip()] = ""
                st.session_state.current_treatment_ep = new_ep_name.strip()
                save_all_data()
                st.rerun()

    current_t_content = st.session_state.ep_treatment_dict.get(current_t_ep, "")
    val_t_content = st.text_area(
        f"📌 [{current_t_ep}] 고정 트리트먼트 (사건 진행 뼈대)",
        value=current_t_content,
        placeholder="예:\n- 씬 1: 지혜원의 추운 겨울밤, 보육원 방 안에서 대화\n- 씬 2: 자정에 소원을 빌다 루돌프의 눈 능력을 개안함\n- 씬 3: 1조의 빚 계약서가 나타나며 경악하는 엔딩",
        height=220,
        key=f"input_treat_{current_t_ep}"
    )
    if st.button(f"💾 [{current_t_ep}] 트리트먼트 저장", key=f"btn_save_treat_{current_t_ep}"):
        st.session_state.ep_treatment_dict[current_t_ep] = val_t_content
        save_all_data()
        st.success(f"[{current_t_ep}] 트리트먼트가 성공적으로 저장되었습니다!")

# 탭 4: 시나리오 주사위
with tab4:
    st.subheader("🎲 4. 시나리오 주사위 (회차별 기발한 전개 발산)")
    st.caption("3번 탭의 고정 트리트먼트와 설정을 바탕으로, 막히는 전개를 풀어낼 다양한 씬 아이디어와 반전 시나리오를 생성합니다.")
    
    all_known_eps_syn = list(st.session_state.ep_treatment_dict.keys())
    c_syn_ep, c_syn_mode = st.columns([2, 2])
    with c_syn_ep:
        target_syn_ep = st.selectbox("발산할 회차 선택", options=all_known_eps_syn, key="target_syn_ep_select")
    with c_syn_mode:
        syn_style_focus = st.selectbox("전개 발산 포커스", [
            "충격적인 반전 및 떡밥 투척 중심",
            "숨막히는 추적 및 위기 탈출 중심",
            "인물 간 날카로운 심리전/대립 중심",
            "감정선 및 드라마틱한 각성 중심"
        ])

    syn_current_treat = st.session_state.ep_treatment_dict.get(target_syn_ep, "")
    st.info(f"🔗 **[연동된 {target_syn_ep} 트리트먼트 뼈대]**: {syn_current_treat if syn_current_treat else '(3번 탭에 입력된 뼈대가 없습니다)'}")
    
    synop_keyword = st.text_area("⚡ 주사위에 던질 추가 자극/키워드 (선택)", placeholder="예: 도파민 터지는 클리프행어 추가, 생각지도 못한 단서 발견", key="syn_keyword_dice", height=75)

    if st.button("🎲 시나리오 주사위 굴리기 (기발한 씬 전개 생성)", key="btn_gen_synopsis_dice"):
        with st.spinner(f"[{target_syn_ep}] 시나리오를 계산 중입니다..."):
            try:
                ctx = build_context_prompt(use_story=True, use_wv=False, use_char_lore=True, use_chars=False, use_synop=False, use_plot=False, use_treatment=False, use_selected_eps=False, use_foreshadow=True, use_compressed=True)
                p = f"""[★ 절대 규칙: {target_syn_ep} 단독 회차 시나리오 주사위 발산]
- 포커스: {syn_style_focus}
- 추가 키워드: "{synop_keyword if synop_keyword.strip() else '최고의 몰입감과 반전'}"

[3단계 고정 트리트먼트 뼈대]:
{syn_current_treat}

[참조 배경 설정]
{ctx}

[출력 양식]
# 🎲 [{target_syn_ep} 시나리오 추천 전개안]
- **씬 1 (도입/긴장 고조)**: 
- **씬 2 (사건 폭발/위기)**: 
- **씬 3 (예상 밖의 반전/절정)**: 
- **씬 4 (엔딩 클리프행어)**: 
- 💡 **집필 팁 (5번 탭 콘티에 복사해 넣을 핵심 한 줄)**:"""
                st.session_state.synopsis = generate_ai(p)
                save_all_data()
                st.rerun()
            except Exception as e:
                st.error(f"시나리오 생성 오류: {e}")

    st.text_area("🎲 생성된 시나리오 결과", value=st.session_state.synopsis, height=250, key="synopsis")
    if st.button("📥 이 시나리오를 5번 탭 콘티란으로 보내기", key="btn_send_syn_to_ep"):
        st.session_state.ep_treatment_guideline = st.session_state.synopsis
        save_all_data()
        st.success("5번 탭으로 전송되었습니다!")

# 탭 5: 3중 본문 집필 & 서재 저장 (4~5,000자 원클릭 완성형 초안 시스템)
with tab5:
    st.subheader("📖 5. 3중 본문 집필 & 실시간 편집기")
    
    available_treatment_keys = list(st.session_state.ep_treatment_dict.keys())
    if not available_treatment_keys:
        available_treatment_keys = ["제1화"]
    
    c_ep1, c_ep2 = st.columns([3, 1])
    with c_ep1:
        st.session_state.current_ep_title = st.text_input("집필할 회차 이름", value=st.session_state.current_ep_title, placeholder="예: 제1화", key="writing_ep_title_input")
    with c_ep2:
        if st.button("📂 서재에서 본문 불러오기"):
            if st.session_state.current_ep_title in st.session_state.episode_list:
                st.session_state.current_ep_content = st.session_state.episode_list[st.session_state.current_ep_title]
                st.success("서재 본문을 불러왔습니다.")
                save_all_data()
                st.rerun()
            else:
                st.warning("서재에 해당 회차 저장본이 없습니다.")

    # 트리트먼트 연동부
    st.markdown("🗺️ **[2단계 연동] 3번 탭 고정 트리트먼트 선택 및 연결**")
    c_t_load1, c_t_load2 = st.columns([3, 1])
    with c_t_load1:
        chosen_t_key = st.selectbox(
            "연결할 3번 탭 트리트먼트 선택", 
            options=available_treatment_keys,
            index=available_treatment_keys.index(st.session_state.current_treatment_ep) if st.session_state.current_treatment_ep in available_treatment_keys else 0,
            key="chosen_t_key_dropdown"
        )
    with c_t_load2:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if st.button("📥 트리트먼트 연동/불러오기", key="btn_apply_chosen_treat"):
            st.session_state.current_treatment_ep = chosen_t_key
            save_all_data()
            st.rerun()

    active_treatment_content = st.session_state.ep_treatment_dict.get(st.session_state.current_treatment_ep, "")
    with st.expander(f"🔗 현재 연결된 [{st.session_state.current_treatment_ep}] 트리트먼트 내용", expanded=False):
        if active_treatment_content.strip():
            st.info(active_treatment_content)
        else:
            st.warning("⚠️ 선택된 트리트먼트 내용이 비어있습니다. 3번 탭에서 뼈대를 작성 후 저장해 주세요.")

    st.markdown("---")

    # 현장 최우선 세부 명령
    st.markdown("⚡ **[현장 최상위 명령] 이번 화 현장 콘티 & 시작 오프닝 초안 (★절대 우선)**")
    val_treatment = st.text_area(
        "이번 화에서 일어날 구체적인 장면, 대사, 초안을 여기에 적으세요. AI가 이 텍스트를 시작점으로 삼아 곧바로 뒷이야기를 이어서 작성합니다.",
        value=st.session_state.ep_treatment_guideline,
        placeholder="예:\n\"리스마스에는 나 보고 싶어서 올지도 모르잖아.\"\n\"......\"\n\"형아는 진짜 바보야.\"\n입을 삐죽 내민 연인이 이불을 뒤집어쓰고 홱 돌아누웠다...",
        height=140,
        key="ep_treatment_guideline"
    )
    if st.button("💾 현장 콘티/초안 저장", key="btn_save_ep_guideline"):
        save_all_data()
        st.success("콘티/초안이 안전하게 저장되었습니다!")

    st.markdown("**접근 여부 설정 (프롬프트 반영 항목)**")
    ec1, ec2, ec3, ec4 = st.columns(4)
    with ec1:
        use_e_story = st.checkbox("1단계: 스토리 원안 (1-1)", value=True, key="ep_story")
    with ec2:
        use_e_char = st.checkbox("1단계: 캐릭터 원안 (2-1)", value=True, key="ep_char_lore")
    with ec3:
        use_e_treat_dict = st.checkbox(f"2단계: [{st.session_state.current_treatment_ep}] 트리트먼트", value=True, key="ep_treat_dict")
    with ec4:
        use_e_eps = st.checkbox("이전 회차 본문 연계", value=False, key="ep_eps")

    col_gen, col_save = st.columns([1, 1])
    with col_gen:
        if st.button("📖 3중 결합 AI 본문 1회차 전체 초안 일괄 집필 (~4,500자)", key="btn_gen_ep_content"):
            with st.spinner(f"[{st.session_state.current_ep_title}] 원안 + 트리트먼트 + 현장 초안을 결합하여 일괄 집필 중입니다..."):
                try:
                    user_starter_draft = st.session_state.ep_treatment_guideline.strip()
                    current_treat_text = active_treatment_content if use_e_treat_dict else ""
                    
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
                    
                    p = f"""[★ 3단계: 작가가 직접 작성한 현장 오프닝 초안 (1순위 절대 준수)]:
\"\"\"
{user_starter_draft if user_starter_draft else '오프닝 지정 없음 - 트리트먼트부터 시작'}
\"\"\"

[★ 2단계: {st.session_state.current_treatment_ep} 회차별 사건 트리트먼트 뼈대 (2순위)]:
\"\"\"
{current_treat_text if current_treat_text else '트리트먼트 없음'}
\"\"\"

[★ 1단계: 기본 인물 및 세계관 원안 (3순위)]:
{ctx}

[집필 지침]
1. [3단계 현장 오프닝 초안]의 상황(인물 대화, 감정선, 호흡)에서 1초도 건너뛰지 말고 곧바로 이어지는 뒷장면을 작성하십시오.
2. [2단계 트리트먼트 뼈대]에 명시된 사건을 반드시 이번 회차 안에 완전히 달성하세요.
3. 성인 시점이나 엉뚱한 비 내리는 날씨 클리셰를 새로 만드는 것을 엄격히 금지합니다.
4. 웹소설 1화 표준 분량(~4,500자)으로 완성된 1회차 본문을 작성해줘."""

                    ai_continuation = generate_ai(p)
                    
                    if user_starter_draft:
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

    st.text_area("작성된 소설 본문 (직접 편집 가능)", value=st.session_state.current_ep_content, height=450, key="current_ep_content")
    if st.button("💾 본문 편집 내용 임시 저장", key="btn_save_ep_content_temp"):
        st.session_state.episode_list[st.session_state.current_ep_title] = st.session_state.current_ep_content
        save_all_data()
        st.success("본문 내용이 저장되었습니다!")
    
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

    st.text_area("💡 작가 메모 / 아이디어 수첩", value=st.session_state.notes, height=120, key="notes")
    if st.button("💾 작가 메모 저장", key="btn_save_notes"):
        save_all_data()
        st.success("메모가 저장되었습니다!")

# 탭 6: 고급 작가 엔진 도구함 (정밀 퇴고 및 윤문)
with tab6:
    st.subheader("🛠️ 작가 전문 집필 & 분석 도구함 Pro")
    
    with st.expander("🎯 1. 문단 정밀 퇴고 및 윤문 도구 (Surgical Rewriter)", expanded=True):
        st.markdown("5번 탭에서 작성된 본문이나 고치고 싶은 특정 문단을 선택해 **프로 작가 수준으로 즉시 윤문**합니다.")
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
                st.session_state.episode_list[st.session_state.current_ep_title] = st.session_state.rewritten_result
                save_all_data()
                st.success("5번 탭 본문으로 적용되었습니다!")

    with st.expander("💬 2. 인물별 고유 말투(보이스) 튜너 (Character Voice Tuner)", expanded=False):
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
                st.session_state.episode_list[st.session_state.current_ep_title] = st.session_state.voice_tuned_res
                save_all_data()
                st.success("5번 탭 본문으로 적용되었습니다!")

    with st.expander("🔍 3. 설정 오류 & 붕괴 탐지기 (Continuity Guard)", expanded=False):
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

    with st.expander("📈 4. 독자 몰입도 & 텐션 그래프 분석기 (Pacing Analyzer)", expanded=False):
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

    with st.expander("⚡ 5. 3가지 분기형 클리프행어(절단신공) 생성기", expanded=False):
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
        
        st.text_area(
            "📌 추적 중인 복선 및 떡밥 목록", 
            value=st.session_state.foreshadowing_list, 
            placeholder="예:\n- [미회수] 1화: 판게아 금고 열쇠의 행방",
            height=180,
            key="foreshadowing_list"
        )
        if st.button("💾 복선 목록 저장", key="btn_save_foreshadow"):
            save_all_data()
            st.success("복선 목록이 저장되었습니다!")

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
        st.markdown("회차가 많아질 때 각 화의 핵심 사건을 3줄로 자동 압축하여 AI 장기 기억 저장소에 보관합니다.")
        
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
                
        st.text_area(
            "📌 전체 회차 압축 줄거리", 
            value=st.session_state.compressed_summaries, 
            height=200,
            key="compressed_summaries"
        )
        if st.button("💾 압축 줄거리 저장", key="btn_save_comp_summaries"):
            save_all_data()
            st.success("압축 줄거리가 저장되었습니다!")
