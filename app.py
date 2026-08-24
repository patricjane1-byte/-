# 탭 3: 시놉시스 (단독 회차 시놉시스 분리 강화)
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
        use_s_story = st.checkbox("고유 스토리", value=True, key="syn_story")
    with sc2:
        use_s_wv = st.checkbox("확장 세계관", value=True, key="syn_wv")
    with sc3:
        use_s_char_lore = st.checkbox("캐릭터 원안", value=True, key="syn_char_lore")
    with sc4:
        use_s_chars = st.checkbox("상세 인물집", value=True, key="syn_chars")
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
