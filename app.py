import streamlit as st
import pandas as pd
import json
import zlib
import struct
import zipfile
import xml.etree.ElementTree as ET
import olefile
from google import genai

st.set_page_config(page_title="웹소설 유니버스 & AI 멀티 채널 스튜디오", page_icon="📚", layout="wide")

# --- 한글/텍스트 파일 추출 함수 ---
def extract_text_from_file(uploaded_file):
    file_bytes = uploaded_file.read()
    file_name = uploaded_file.name.lower()
    try:
        if file_name.endswith(".hwpx"):
            import io
            with zipfile.ZipFile(io.BytesIO(file_bytes), 'r') as z:
                section_names = [name for name in z.namelist() if name.startswith("Contents/section")]
                text_list = []
                for s in sorted(section_names):
                    xml_content = z.read(s)
                    root = ET.fromstring(xml_content)
                    for elem in root.iter():
                        if elem.tag.endswith('t') and elem.text:
                            text_list.append(elem.text)
                return "\n".join(text_list)
        elif file_name.endswith(".hwp"):
            import io
            f = olefile.OleFileIO(io.BytesIO(file_bytes))
            dirs = f.listdir()
            header = f.openstream("FileHeader").read()
            is_compressed = (header[36] & 1) == 1
            nums = [int(d[1][len("Section"):]) for d in dirs if d[0] == "BodyText"]
            sections = ["BodyText/Section" + str(x) for x in sorted(nums)]
            full_text = []
            for sec in sections:
                data = f.openstream(sec).read()
                if is_compressed:
                    data = zlib.decompress(data, -15)
                i = 0
                while i < len(data):
                    header = struct.unpack_from("<I", data, i)[0]
                    tag_id = header & 0x3FF
                    length = (header >> 20) & 0xFFF
                    if length == 0xFFF:
                        length = struct.unpack_from("<I", data, i + 4)[0]
                        i += 4
                    i += 4
                    if tag_id == 67:
                        para_bytes = data[i:i+length]
                        text = para_bytes.decode('utf-16le', errors='ignore')
                        clean_text = "".join(ch for ch in text if ord(ch) >= 32 or ch in "\n\r\t")
                        full_text.append(clean_text)
                    i += length
            return "\n".join(full_text)
        else:
            return file_bytes.decode('utf-8', errors='ignore')
    except Exception as e:
        return f"파일 분석 오류: {str(e)}"

# --- [공유 유니버스 공통 세계관 초기 데이터] ---
if "shared_universe_db" not in st.session_state:
    st.session_state.shared_universe_db = pd.DataFrame([
        {
            "설정 항목명": "흑막 배후 조직 (팬텀)",
            "보안 등급": "🟡 명칭 언급 봉인",
            "세부 설정 및 진실": "정재계 고위직과 연루되어 도심 지하 범죄를 조율하는 사설 픽서 집단",
            "공개 단서 코멘트": "어떤 작품에서든 조직의 범행과 흔적은 다루되 고유명칭 '팬텀'은 발설 금지"
        },
        {
            "설정 항목명": "지하 3호선 폐쇄 역의 비밀 통로",
            "보안 등급": "🟢 전면 공개",
            "세부 설정 및 진실": "밀수 조직과 부패 관료가 오가는 비공식 탈출 루트",
            "공개 단서 코멘트": "도시 내 이동 통로로 자연스럽게 등장시킬 것"
        }
    ])

# --- [작품별 독립 채널 데이터베이스 구조] ---
if "novel_channels" not in st.session_state:
    st.session_state.novel_channels = {
        "작품 1: 도심 실종 추적기": {
            "characters_df": pd.DataFrame([
                {
                    "인물명": "이육사",
                    "보안 등급": "🟢 전면 공개",
                    "역할/소속": "실종 사건 전문 추적관 / 주인공",
                    "고유 말투": "덤덤하고 냉소적인 단답형. 감정 절제",
                    "타인 인지 정보 (지식 수위)": "추수국(Lv 2: 파트너), 황대수(Lv 0: 미면식)",
                    "공개 단서 코멘트": "주인공 시점으로 자유롭게 전개"
                },
                {
                    "인물명": "추수국",
                    "보안 등급": "🟢 전면 공개",
                    "역할/소속": "사설 정보원 겸 트래커 / 파트너",
                    "고유 말투": "능글맞고 빈정거리는 톤. 반어법 사용",
                    "타인 인지 정보 (지식 수위)": "이육사(Lv 2: 수사관), 황대수(Lv 3: 악명과 채권 관계를 알아 경계함)",
                    "공개 단서 코멘트": "이육사와 대화 핑퐁 위주. 황대수 비밀은 직접 발설 금지"
                },
                {
                    "인물명": "황대수",
                    "보안 등급": "🟡 이름 언급 봉인",
                    "역할/소속": "탈옥한 연쇄 실종 주범 / 빌런",
                    "고유 말투": "낮게 깔리는 거친 쇳소리",
                    "타인 인지 정보 (지식 수위)": "이육사(Lv 0: 모름), 추수국(Lv 2: 정보원으로 인지)",
                    "공개 단서 코멘트": "체격과 흉터는 묘사하되 '황대수' 실명은 발설 금지 ('그놈'으로 지칭)"
                }
            ]),
            "local_settings_df": pd.DataFrame([
                {
                    "설정 항목명": "1화 발생 사건 (서부 부두 실종 사건)",
                    "보안 등급": "🟢 전면 공개",
                    "세부 설정 및 진실": "밀항선 주변에서 발견된 의문의 혈흔과 깨진 시계",
                    "공개 단서 코멘트": "현장 단서로 자연스럽게 노출"
                }
            ]),
            "use_shared_universe": True,
            "context_text": "",
            "foreshadow_list": "",
            "custom_style_rules": "단문 위주의 건조하고 빠른 호흡. 불필요한 번역투 배제. 감각적 지문 위주.",
            "candidates": "",
            "selected_synopsis": "",
            "final_novel": "",
            "polished_novel": "",
            "scan_report": None
        },
        "작품 2: 신규 기획작": {
            "characters_df": pd.DataFrame([
                {
                    "인물명": "신규 주인공",
                    "보안 등급": "🟢 전면 공개",
                    "역할/소속": "잠입 수사관",
                    "고유 말투": "차분하고 논리적인 어조",
                    "타인 인지 정보 (지식 수위)": "주변 인물들(Lv 0: 미면식)",
                    "공개 단서 코멘트": "독백 위주 전개"
                }
            ]),
            "local_settings_df": pd.DataFrame([
                {
                    "설정 항목명": "독립 사건 A",
                    "보안 등급": "🟢 전면 공개",
                    "세부 설정 및 진실": "사건의 기본 진실",
                    "공개 단서 코멘트": "자유롭게 공개"
                }
            ]),
            "use_shared_universe": True,
            "context_text": "",
            "foreshadow_list": "",
            "custom_style_rules": "빠른 호흡과 긴장감 넘치는 문체.",
            "candidates": "",
            "selected_synopsis": "",
            "final_novel": "",
            "polished_novel": "",
            "scan_report": None
        }
    }

if "current_channel" not in st.session_state:
    st.session_state.current_channel = "작품 1: 도심 실종 추적기"

# --- 사이드바: 채널(작품) 관리 및 환경 설정 ---
with st.sidebar:
    st.header("🗂️ 작품 채널 관리")
    channel_list = list(st.session_state.novel_channels.keys())
    selected_ch = st.selectbox("현재 작업 채널 선택", channel_list, index=channel_list.index(st.session_state.current_channel))
    st.session_state.current_channel = selected_ch

    # 새 작품 채널 생성
    with st.expander("➕ 새 작품 채널 만들기"):
        new_ch_name = st.text_input("새 작품 이름")
        if st.button("채널 생성"):
            if new_ch_name and new_ch_name not in st.session_state.novel_channels:
                st.session_state.novel_channels[new_ch_name] = {
                    "characters_df": pd.DataFrame([
                        {"인물명": "주인공", "보안 등급": "🟢 전면 공개", "역할/소속": "역할", "고유 말투": "말투", "타인 인지 정보 (지식 수위)": "초면(Lv 0)", "공개 단서 코멘트": "자유 공개"}
                    ]),
                    "local_settings_df": pd.DataFrame([
                        {"설정 항목명": "신규 설정", "보안 등급": "🟢 전면 공개", "세부 설정 및 진실": "내용", "공개 단서 코멘트": "자유 공개"}
                    ]),
                    "use_shared_universe": True,
                    "context_text": "",
                    "foreshadow_list": "",
                    "custom_style_rules": "단문 위주의 빠른 호흡.",
                    "candidates": "",
                    "selected_synopsis": "",
                    "final_novel": "",
                    "polished_novel": "",
                    "scan_report": None
                }
                st.session_state.current_channel = new_ch_name
                st.success(f"'{new_ch_name}' 채널이 생성되었습니다!")
                st.rerun()

    st.markdown("---")
    st.header("🌐 공용 유니버스 세계관 연동")
    cur_data = st.session_state.novel_channels[st.session_state.current_channel]
    cur_data["use_shared_universe"] = st.checkbox("이 작품에 공용 유니버스 설정 공유/연동", value=cur_data["use_shared_universe"])

    st.markdown("---")
    st.header("⚙️ API & 파일 로드")
    api_key = st.text_input("Gemini API Key", type="password", help="Google AI Studio API Key")

    uploaded_file = st.file_uploader("📂 소설 파일 로드 (.hwp, .hwpx, .txt)", type=["hwp", "hwpx", "txt"])
    if uploaded_file is not None:
        if st.button("파일 원고 로드하기", use_container_width=True):
            extracted = extract_text_from_file(uploaded_file)
            cur_data["context_text"] = extracted
            st.success(f"'{uploaded_file.name}' 로딩 완료!")

    st.markdown("---")
    st.header("🖋️ 문체 DNA 분석실")
    sample_style_text = st.text_area("문체 샘플 붙여넣기", height=80)
    if st.button("🔍 문체 분석 & 적용", use_container_width=True):
        if api_key and sample_style_text.strip():
            with st.spinner("문체 분석 중..."):
                client = genai.Client(api_key=api_key)
                res = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=f"다음 텍스트의 핵심 문체 규칙을 4~5줄로 정리하세요:\n{sample_style_text}"
                )
                cur_data["custom_style_rules"] = res.text
                st.success("문체 분석 완료!")

    cur_data["custom_style_rules"] = st.text_area("적용된 문체 규칙", value=cur_data["custom_style_rules"], height=80)

# 현재 채널 데이터 바인딩
cur_channel = st.session_state.current_channel
cur_data = st.session_state.novel_channels[cur_channel]

# 메인 헤더
st.title(f"📖 {cur_channel}")
st.caption("독립 캐릭터 DB • 공유 유니버스 연동 • 4단계 보안 마스킹 • 인지 수위(Lv 0~3) 통제 • AI 집필실")

col1, col2 = st.columns([1, 1])

# [왼쪽 열: 캐릭터 DB, 작품 개별 세계관 DB, 공용 유니버스 DB, 주사위]
with col1:
    tab_char, tab_local_world, tab_shared_world = st.tabs(["👤 캐릭터 DB", "📖 본 작품 고유 설정", "🌐 공유 유니버스 세계관"])
    
    with tab_char:
        st.caption("현재 작품에만 등장하는 캐릭터의 보안 등급과 타인 인지 수위(Lv 0~3)입니다.")
        edited_chars = st.data_editor(
            cur_data["characters_df"],
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "인물명": st.column_config.TextColumn("인물명", width="small"),
                "보안 등급": st.column_config.SelectboxColumn(
                    "보안 등급",
                    options=["🟢 전면 공개", "🟡 이름 언급 봉인", "🟠 정체/직업 봉인", "🔴 전면 봉인"],
                    default="🟢 전면 공개",
                    width="medium"
                ),
                "역할/소속": st.column_config.TextColumn("역할/소속", width="medium"),
                "고유 말투": st.column_config.TextColumn("말투 특징", width="medium"),
                "타인 인지 정보 (지식 수위)": st.column_config.TextColumn("타인 인지 수위 (Lv 0~3)", width="large"),
                "공개 단서 코멘트": st.column_config.TextColumn("작가 코멘트 (단서 조항)", width="large"),
            }
        )
        cur_data["characters_df"] = edited_chars

    with tab_local_world:
        st.caption("이 작품에만 국한된 고유 사건 및 지리적 설정입니다.")
        edited_local_world = st.data_editor(
            cur_data["local_settings_df"],
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "설정 항목명": st.column_config.TextColumn("설정/사건 항목명", width="medium"),
                "보안 등급": st.column_config.SelectboxColumn(
                    "보안 등급",
                    options=["🟢 전면 공개", "🟡 명칭 언급 봉인", "🟠 세부내용/진실 봉인", "🔴 전면 봉인"],
                    default="🟢 전면 공개",
                    width="medium"
                ),
                "세부 설정 및 진실": st.column_config.TextColumn("세부 설정 및 진실", width="large"),
                "공개 단서 코멘트": st.column_config.TextColumn("작가 코멘트 (단서 조항)", width="large"),
            }
        )
        cur_data["local_settings_df"] = edited_local_world

    with tab_shared_world:
        st.caption("모든 작품 채널에서 함께 공유하는 거대 유니버스 설정(배후 조직, 도시 법칙 등)입니다.")
        edited_shared = st.data_editor(
            st.session_state.shared_universe_db,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "설정 항목명": st.column_config.TextColumn("공용 설정 항목명", width="medium"),
                "보안 등급": st.column_config.SelectboxColumn(
                    "보안 등급",
                    options=["🟢 전면 공개", "🟡 명칭 언급 봉인", "🟠 세부내용/진실 봉인", "🔴 전면 봉인"],
                    default="🟢 전면 공개",
                    width="medium"
                ),
                "세부 설정 및 진실": st.column_config.TextColumn("공용 진실/설정", width="large"),
                "공개 단서 코멘트": st.column_config.TextColumn("공용 단서 조항", width="large"),
            }
        )
        st.session_state.shared_universe_db = edited_shared

    st.markdown("---")
    st.subheader("📖 2. 누적 원고 맥락")
    cur_data["context_text"] = st.text_area("누적 줄거리 요약", value=cur_data["context_text"], height=90)

    st.markdown("---")
    st.subheader("📌 3. 미회수 복선 / 떡밥 관리")
    if st.button("🔍 AI 원고 분석: 미회수 복선 자동 추출", use_container_width=True):
        if api_key and cur_data["context_text"]:
            with st.spinner("복선 분석 중..."):
                client = genai.Client(api_key=api_key)
                res = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=f"원고에서 미회수 복선을 리스트로 정리하세요:\n{cur_data['context_text'][-4000:]}"
                )
                cur_data["foreshadow_list"] = res.text

    cur_data["foreshadow_list"] = st.text_area("미회수 복선", value=cur_data["foreshadow_list"], height=60)
    use_foreshadow = st.checkbox("🎯 이번 화에 복선 반영하기", value=True)

    st.markdown("---")
    if st.button("🎲 4. 기발한 에피소드 시놉시스 주사위 굴리기 (Reroll)", use_container_width=True, type="primary"):
        if not api_key:
            st.warning("사이드바에 API Key를 입력하세요.")
        else:
            with st.spinner("캐릭터 인지 수위와 유니버스 설정을 조합하여 시놉시스 생성 중..."):
                client = genai.Client(api_key=api_key)
                
                # 캐릭터 규칙
                char_rules = "\n[등장인물 보안/인지 정보]:\n"
                for _, row in cur_data["characters_df"].iterrows():
                    char_rules += f"- 인물: {row['인물명']} | 등급: [{row['보안 등급']}] | 인지상태: [{row['타인 인지 정보 (지식 수위)']}] | 지침: {row['공개 단서 코멘트']}\n"

                # 세계관 규칙 (고유 설정 + 유니버스 공유 설정 결합)
                world_rules = "\n[본 작품 고유 세계관 지침]:\n"
                for _, row in cur_data["local_settings_df"].iterrows():
                    world_rules += f"- 고유항목: {row['설정 항목명']} | 등급: [{row['보안 등급']}] | 진실: {row['세부 설정 및 진실']} | 지침: {row['공개 단서 코멘트']}\n"
                
                if cur_data["use_shared_universe"]:
                    world_rules += "\n[🌐 공용 유니버스 세계관 지침 (타 작품과 공유됨)]:\n"
                    for _, row in st.session_state.shared_universe_db.iterrows():
                        world_rules += f"- 유니버스항목: {row['설정 항목명']} | 등급: [{row['보안 등급']}] | 진실: {row['세부 설정 및 진실']} | 지침: {row['공개 단서 코멘트']}\n"

                foreshadow_inst = f"\n[복선]: {cur_data['foreshadow_list']}" if (use_foreshadow and cur_data["foreshadow_list"].strip()) else ""

                prompt = f"""
당신은 베스트셀러 웹소설 메인 플롯 기획자입니다.
아래의 [캐릭터 인지 정보]와 [세계관 보안 지침]을 철저히 준수하여 다음 화 시놉시스 3가지를 기획하세요.

{char_rules}
{world_rules}
{foreshadow_inst}

[누적 원고 맥락]:
{cur_data['context_text'][-4000:]}

[후보 1] (파격 반전형) :
[후보 2] (인물 갈등 폭발형) :
[후보 3] (미스터리/돌발 변수형) :
"""
                res = client.models.generate_content(model='gemini-1.5-flash', contents=prompt)
                cur_data["candidates"] = res.text

    if cur_data["candidates"]:
        st.markdown("### 💡 주사위 결과")
        st.text_area("시놉시스 후보들", value=cur_data["candidates"], height=130)

# [오른쪽 열: POV 선택, 본문 집필, 퇴고, 스캐너, 동기화]
with col2:
    st.subheader("✏️ 5. 시놉시스 선택 & 이번 화 POV(시점) 설정")
    
    col_c1, col_c2 = st.columns([1, 1])
    with col_c1:
        load_choice = st.selectbox("후보 선택", ["[후보 1] 불러오기", "[후보 2] 불러오기", "[후보 3] 불러오기"])
    with col_c2:
        if st.button("📥 선택한 후보 불러오기"):
            if cur_data["candidates"]:
                tag = load_choice.split("]")[0] + "]"
                if tag in cur_data["candidates"]:
                    parts = cur_data["candidates"].split(tag)
                    cur_data["selected_synopsis"] = f"{tag}\n{parts[1].split('[후보')[0].strip()}"
                else:
                    cur_data["selected_synopsis"] = cur_data["candidates"]

    char_names = list(cur_data["characters_df"]["인물명"])
    pov_char = st.selectbox("👁️ 이번 화 시점 인물 (POV)", char_names if char_names else ["주인공"])

    cur_data["selected_synopsis"] = st.text_area("최종 집필용 시놉시스 (작가 한 줄 추가 가능)", value=cur_data["selected_synopsis"], height=80)

    if st.button("🚀 POV 인지 제한 적용하여 4,000~5,000자 본문 집필하기", type="primary", use_container_width=True):
        if not api_key or not cur_data["selected_synopsis"].strip():
            st.warning("API Key와 시놉시스를 확인하세요.")
        else:
            with st.spinner("시점자의 인지 수위와 유니버스 보안 헌법을 강제하며 본문 집필 중..."):
                client = genai.Client(api_key=api_key)
                
                char_rules = "\n[★ 캐릭터 보안 및 인지 수위]:\n"
                for _, row in cur_data["characters_df"].iterrows():
                    char_rules += f"- {row['인물명']}: [{row['보안 등급']}] (말투: '{row['고유 말투']}', 인지상태: '{row['타인 인지 정보 (지식 수위)']}', 지침: '{row['공개 단서 코멘트']}')\n"

                world_rules = "\n[★ 고유 세계관 보안 지침]:\n"
                for _, row in cur_data["local_settings_df"].iterrows():
                    world_rules += f"- {row['설정 항목명']}: [{row['보안 등급']}] (진실: '{row['세부 설정 및 진실']}', 지침: '{row['공개 단서 코멘트']}')\n"

                if cur_data["use_shared_universe"]:
                    world_rules += "\n[★ 🌐 공용 유니버스 보안 지침]:\n"
                    for _, row in st.session_state.shared_universe_db.iterrows():
                        world_rules += f"- {row['설정 항목명']}: [{row['보안 등급']}] (진실: '{row['세부 설정 및 진실']}', 지침: '{row['공개 단서 코멘트']}')\n"

                prompt = f"""
당신은 최고 인기 웹소설 작가입니다.
아래의 [문체 DNA], [POV 시점 헌법], [캐릭터/유니버스 보안 지침]을 철저히 지키며 본문을 집필하세요.

[문체 DNA]:
{cur_data['custom_style_rules']}

[★ 핵심 헌법 - 시점자({pov_char}) 인지 제한 규칙]:
1. 이번 화는 철저히 '{pov_char}'의 시점입니다.
2. {pov_char}가 통성명하지 않았거나 인지 정보가 'Lv 0'인 인물은 대사와 지문에서 절대 실명을 알 수 없습니다. 오직 외형 특징('가죽 재킷 사내', '절름발이')으로만 묘사하세요.
3. {pov_char}가 알지 못하는 비밀/과거/배후 조직명을 전지적 독심술 형태로 발설하는 것을 엄격히 금지합니다.

{char_rules}
{world_rules}

[시놉시스]:
{cur_data['selected_synopsis']}

[필수 규칙]:
- 공백 포함 4,000~5,000자 내외로 작성하세요.
- 대사와 지문 핑퐁의 긴장감을 극대화하고, 엔딩은 충격적인 절단신공으로 마무리하세요.
"""
                res = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
                cur_data["final_novel"] = res.text
                cur_data["polished_novel"] = res.text
                cur_data["scan_report"] = None

    if cur_data["final_novel"]:
        st.text_area("초안 원고", value=cur_data["final_novel"], height=130)

        st.markdown("---")
        st.subheader("🛠️ 6. AI 맞춤 퇴고실")
        preset = st.selectbox("퇴고 프리셋", ["인물별 말투 개성 살리기", "하드보일드/긴장감 강화", "속도감 극대화", "직접 지시"])
        custom_inst = st.text_input("추가 맞춤 지시", placeholder="예: '이육사의 대사를 더 덤덤하게 깎아줘.'")
        
        if st.button("🔄 본문 퇴고 실행", use_container_width=True):
            with st.spinner("퇴고 리라이팅 중..."):
                client = genai.Client(api_key=api_key)
                prompt = f"아래 본문을 작가의 퇴고 지침({preset} / {custom_inst})에 맞춰 리라이팅하세요:\n{cur_data['polished_novel']}"
                res = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
                cur_data["polished_novel"] = res.text
                cur_data["scan_report"] = None
                st.success("퇴고 완료!")

        st.text_area("최종 완성 원고", value=cur_data["polished_novel"], height=150)

        # --- [7. 보안 & 인지오류 스캐너] ---
        st.markdown("---")
        st.subheader("🛡️ 7. 다단계 보안 & 인지 무결성 검증")
        col_s1, col_s2 = st.columns([1, 1])
        with col_s1:
            if st.button("🔍 보안 위반 & 독심술 오류 스캔", type="primary", use_container_width=True):
                with st.spinner("실명 유출, 유니버스 설정 위반, 초면 독심술 여부 검사 중..."):
                    client = genai.Client(api_key=api_key)
                    
                    audit_rules = f"\n[검증 기준 - POV 시점자: {pov_char}]:\n"
                    for _, row in cur_data["characters_df"].iterrows():
                        audit_rules += f"- 인물 '{row['인물명']}': 등급 [{row['보안 등급']}], 인지상태 [{row['타인 인지 정보 (지식 수위)']}], 지침 [{row['공개 단서 코멘트']}]\n"
                    for _, row in cur_data["local_settings_df"].iterrows():
                        audit_rules += f"- 고유설정 '{row['설정 항목명']}': 등급 [{row['보안 등급']}], 지침 [{row['공개 단서 코멘트']}]\n"
                    if cur_data["use_shared_universe"]:
                        for _, row in st.session_state.shared_universe_db.iterrows():
                            audit_rules += f"- 공용유니버스 '{row['설정 항목명']}': 등급 [{row['보안 등급']}], 지침 [{row['공개 단서 코멘트']}]\n"

                    prompt = f"""
당신은 최고 수준의 소설 보안 및 개연성 검수관입니다.
아래 [검증 기준]과 [완성 원고]를 대조하여 다음 위반 사항이 있는지 스캔하세요:
1. 보안 등급 위반 (이름 봉인인데 실명 노출, 정체 봉인인데 비밀 누설)
2. 인지 오류 / 독심술 (시점자 '{pov_char}'가 아직 모르는 인물의 이름을 부르거나 모르는 과거를 알고 있는지)
3. 작가 단서 코멘트 위반

{audit_rules}

[완성 원고]:
{cur_data['polished_novel']}

[출력 양식]:
- 위반 발견 시: 🚨 [위반/인지오류 감지] -> 위치 지목, 위반 내용, 수정 권고안
- 위반 없을 시: ✅ [무결성 통과] 모든 보안 등급과 인지 수위가 정상입니다.
"""
                    res = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
                    cur_data["scan_report"] = res.text

        with col_s2:
            st.download_button("💾 원고 다운로드(.txt)", data=cur_data["polished_novel"], file_name=f"{cur_channel}_최종원고.txt", use_container_width=True)

        if cur_data["scan_report"]:
            if "🚨" in cur_data["scan_report"]:
                st.error("⚠️ 보안/인지 위반 사항이 감지되었습니다!")
            else:
                st.success("✅ 검증 완료!")
            st.info(cur_data["scan_report"])

        # --- [8. 인지 수위(Lv 0~3) 자동 동기화] ---
        st.markdown("---")
        st.subheader("🔄 8. 인지 수위 & 캐릭터 상태 자동 동기화")
        st.caption("이번 화에서 인물들이 새로 알게 된 사실(Lv 0→Lv 2 통성명 등)을 DB에 자동 반영합니다.")

        if st.button("✨ 이번 화 사건으로 인지 수위 & DB 자동 동기화", use_container_width=True):
            with st.spinner("원고 분석 및 인지 수위 갱신 중..."):
                client = genai.Client(api_key=api_key)
                sync_prompt = f"""
당신은 소설 데이터 아카이빙 전문가입니다.
아래 [완성 원고]를 읽고, 이번 화에서 발생한 사건에 따라 등장인물들의 변화를 JSON으로만 출력하세요.
- 통성명을 했거나 신원을 파악했다면 타인 인지 수위를 갱신 (예: '황대수(Lv 2: 얼굴과 이름을 알게 됨)')
- 신규 인물이나 설정이 등장했다면 추가

[완성 원고]:
{cur_data['polished_novel']}

[출력 형식 - JSON만 출력]:
{{
  "updated_characters": [
    {{
      "인물명": "이육사",
      "새로운_인지_정보": "추수국(Lv 2: 파트너), 황대수(Lv 1: 얼굴을 직접 목격하고 흉터를 확인했으나 이름은 모름)"
    }}
  ],
  "new_characters": [],
  "new_settings": []
}}
"""
                try:
                    res = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=sync_prompt,
                        config={'response_mime_type': 'application/json'}
                    )
                    data = json.loads(res.text)
                    
                    for update in data.get("updated_characters", []):
                        mask = cur_data["characters_df"]["인물명"] == update["인물명"]
                        if mask.any():
                            cur_data["characters_df"].loc[mask, "타인 인지 정보 (지식 수위)"] = update["새로운_인지_정보"]
                    
                    if data.get("new_characters"):
                        cur_data["characters_df"] = pd.concat([cur_data["characters_df"], pd.DataFrame(data["new_characters"])], ignore_index=True)
                    if data.get("new_settings"):
                        cur_data["local_settings_df"] = pd.concat([cur_data["local_settings_df"], pd.DataFrame(data["new_settings"])], ignore_index=True)
                    
                    st.success("인지 수위 및 DB 동기화 완료! 왼쪽 탭에서 갱신된 내용을 확인하세요.")
                    st.rerun()
                except Exception as e:
                    st.error(f"동기화 오류: {str(e)}")
