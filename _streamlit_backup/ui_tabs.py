import streamlit as st
import pandas as pd
import plotly.express as px
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode

from config import ROLES
from equipment.db import load_data, save_photo_changes, get_branches
from events.db import get_treatment_descriptions
from auth import hash_password
from users import (
    load_users, add_user, remove_user,
    update_user_role, update_user_password, update_user_memo,
    invalidate_users_cache, ensure_memo_column,
)


# ============================================================
# KPI 카드 헬퍼
# ============================================================
def _kpi_card(icon, label, value, color="var(--accent)"):
    """아이콘 + 라벨 + 대형 숫자 + 좌측 컬러 보더 카드"""
    return f"""
    <div style="background:var(--bg-card); border:1px solid var(--border);
                border-left:4px solid {color}; border-radius:var(--radius, 10px);
                padding:1rem 1.25rem; box-shadow:var(--shadow-sm, 0 1px 2px rgba(0,0,0,0.05));
                transition:all 0.2s ease; height:100%;">
        <div style="display:flex;align-items:center;gap:0.4rem;margin-bottom:0.3rem;">
            <span style="font-size:1.15rem;">{icon}</span>
            <span style="font-size:0.72rem;font-weight:600;text-transform:uppercase;
                         letter-spacing:0.04em;color:var(--text-muted, #94A3B8);">{label}</span>
        </div>
        <div style="font-size:1.65rem;font-weight:700;color:var(--text-primary, #1E293B);line-height:1.2;">
            {value}
        </div>
    </div>"""


# ============================================================
# 탭 1: 장비 관리 (서브 뷰 전환)
# ============================================================
def render_tab_equipment(filtered_df, df, selected_branches, permissions):
    """보유장비 탭 — 상단 필터 + 서브 뷰 전환"""
    # ── 상단 필터 바 ──
    col_f1, col_f2 = st.columns([1.5, 3])
    with col_f1:
        _cats = sorted(filtered_df["카테고리"].unique()) if len(filtered_df) > 0 else []
        eq_cat = st.selectbox("카테고리", ["전체"] + _cats, key="eq_top_cat")
    with col_f2:
        eq_search = st.text_input("장비명 검색", placeholder="장비명을 입력하세요", key="eq_top_search")

    # 카테고리 / 검색 필터 적용
    if eq_cat != "전체":
        filtered_df = filtered_df[filtered_df["카테고리"] == eq_cat]
    if eq_search:
        _mask = (
            filtered_df["기기명"].str.contains(eq_search, case=False, na=False)
            | filtered_df["장비그룹"].str.contains(eq_search, case=False, na=False)
        )
        filtered_df = filtered_df[_mask]

    # ── 서브 뷰 (라디오 + 건수 한 줄) ──
    col_radio, col_count = st.columns([3, 1])
    with col_radio:
        sub_view = st.radio(
            "보기 선택", ["장비 목록", "장비 검색", "지점 비교"],
            horizontal=True, label_visibility="collapsed",
        )
    with col_count:
        st.markdown(
            f"<div style='text-align:right; font-size:0.85rem; font-weight:600; "
            f"color:var(--text-secondary,#64748B); padding-top:0.45rem;'>"
            f"{len(filtered_df):,}건</div>",
            unsafe_allow_html=True,
        )
    if sub_view == "장비 목록":
        render_tab_equipment_list(filtered_df, df, selected_branches, permissions)
    elif sub_view == "장비 검색":
        render_tab_search(filtered_df, df)
    elif sub_view == "지점 비교":
        render_tab_compare(df, selected_branches)


def _aggrid_dark_css():
    """AG-Grid 공통 커스텀 CSS (라이트 + 다크 모드)."""
    return {
        ".ag-center-header": {"text-align": "center !important"},
        ".ag-header-cell-label": {"justify-content": "center"},
        ".ag-cell": {"padding": "0 6px !important", "line-height": "28px !important"},
        ".ag-header-cell": {"padding": "0 6px !important"},
        ".ag-row": {"font-size": "13px"},
        ".ag-cell-wrapper": {"justify-content": "center"},
        ".ag-checkbox-input-wrapper": {"margin": "0 auto"},
        ".ag-header": {"background-color": "#F8FAFC !important", "border-bottom": "2px solid #2563EB !important"},
        ".ag-header-cell": {"background-color": "#F8FAFC !important", "color": "#1E293B !important",
                            "padding": "0 6px !important", "font-weight": "600 !important"},
        ".ag-row-odd": {"background-color": "#FAFBFC !important"},
        ".ag-row-hover": {"background-color": "#EFF6FF !important"},
        ".ag-root-wrapper": {"border": "1px solid #E2E8F0 !important", "border-radius": "8px !important"},
        ":root.dark-theme .ag-cell": {"color": "#E0E0E0 !important", "border-color": "#2A2A4A !important"},
        ":root.dark-theme .ag-header": {"background-color": "#1E293B !important", "border-bottom": "2px solid #3B82F6 !important"},
        ":root.dark-theme .ag-header-cell": {"background-color": "#1E293B !important", "color": "#F1F5F9 !important"},
        ":root.dark-theme .ag-header-cell-label": {"color": "#F1F5F9 !important"},
        ":root.dark-theme .ag-row": {"background-color": "#0F172A !important", "color": "#E0E0E0 !important"},
        ":root.dark-theme .ag-root-wrapper": {"background-color": "#0F172A !important", "border-color": "#334155 !important"},
        ":root.dark-theme .ag-row-odd": {"background-color": "#1E293B !important"},
        ":root.dark-theme .ag-row-hover": {"background-color": "#1E3A5F !important"},
        ":root.dark-theme .ag-body-viewport": {"background-color": "#0F172A !important"},
    }


@st.dialog("조회", width="large")
def _show_lookup_dialog(equip_name: str, branch_name: str, selected_branches: list):
    """시술 정보 + 관련 이벤트를 통합 표시하는 다이얼로그."""
    import re
    from equipment.db import search_device_info
    from config import DEVICE_ALIASES

    # ── 헤더 ──
    st.markdown(
        f"<div style='font-size:1.15rem; font-weight:700; color:var(--text-primary,#1E293B); margin-bottom:0.25rem;'>"
        f"<span style='color:var(--accent,#2563EB);'>{equip_name}</span></div>",
        unsafe_allow_html=True,
    )

    # ── 0. 부위 수식어 제거 (바디/얼굴 등 괄호 안 부위는 장비명이 아님) ──
    core_name = re.sub(r"\s*[(\（][^)\）]*[)\）]", "", equip_name).strip()
    if not core_name:
        core_name = equip_name.strip()

    # ── 1. 시술 정보 (DB) — 양방향 부분 매칭 ──
    from equipment.db import find_matching_devices

    device_matched = find_matching_devices(core_name)

    # DEVICE_ALIASES 보조 매칭 (DB에 없는 별칭 커버)
    if not device_matched:
        seen_names = set()
        name_lower = core_name.lower()
        for canonical, aliases in DEVICE_ALIASES.items():
            for alias in aliases:
                if alias.lower() in name_lower or name_lower in alias.lower():
                    results = search_device_info(canonical)
                    for r in results:
                        if r["name"] not in seen_names:
                            device_matched.append(r)
                            seen_names.add(r["name"])
                    break

    # 이벤트 검색용 키워드는 모든 매칭 결과 보존 (써마지FLX → 써마지 이벤트도 찾기)
    all_matched_names = [r["name"] for r in device_matched]

    # 시술 정보 카드 표시용: 정확 매칭이 있으면 부모(부분 매칭) 항목은 제거
    exact_names = {r["name"] for r in device_matched if r["name"].lower() == core_name.lower()}
    if exact_names:
        device_display = [r for r in device_matched if r["name"] in exact_names]
    else:
        device_display = device_matched

    if device_display:
        for info in device_display:
            st.markdown(f"""
<div style="background:var(--bg-card,#F8FAFC); border:1px solid var(--border,#E2E8F0);
    border-left:4px solid var(--accent,#2563EB); border-radius:8px; padding:0.75rem 1rem; margin-bottom:0.5rem;">
    <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.35rem;">
        <span style="font-size:0.95rem; font-weight:700; color:var(--text-primary,#1E293B);">{info['name']}</span>
        <span style="font-size:0.7rem; color:var(--text-muted,#94A3B8);
            background:var(--secondary-background-color,#F1F5F9); padding:1px 7px; border-radius:4px;">{info.get('category', '')}</span>
    </div>
    <div style="font-size:0.85rem; color:var(--text-primary,#334155); line-height:1.6; margin-bottom:0.35rem;">
        {info.get('summary', '')}
    </div>
    <table style="font-size:0.78rem; color:var(--text-primary,#475569); border-collapse:collapse; width:100%;">
        <tr style="border-bottom:1px solid var(--border,#E2E8F0);">
            <td style="padding:0.25rem 0.4rem; font-weight:600; white-space:nowrap; width:70px; color:var(--text-muted,#64748B);">적용 부위</td>
            <td style="padding:0.25rem 0.4rem;">{info.get('target', '-')}</td>
        </tr>
        <tr style="border-bottom:1px solid var(--border,#E2E8F0);">
            <td style="padding:0.25rem 0.4rem; font-weight:600; white-space:nowrap; color:var(--text-muted,#64748B);">작용 원리</td>
            <td style="padding:0.25rem 0.4rem;">{info.get('mechanism', '-')}</td>
        </tr>
        <tr>
            <td style="padding:0.25rem 0.4rem; font-weight:600; white-space:nowrap; color:var(--text-muted,#64748B);">참고</td>
            <td style="padding:0.25rem 0.4rem;">{info.get('note', '-')}</td>
        </tr>
    </table>
</div>""", unsafe_allow_html=True)
    else:
        st.caption(f"'{equip_name}'에 대한 시술 정보가 등록되어 있지 않습니다.")

    # ── 2. 관련 이벤트 ──
    st.markdown(
        "<div style='font-size:0.9rem; font-weight:700; color:var(--text-primary,#1E293B); "
        "margin:0.5rem 0 0.25rem 0; border-top:1px solid var(--border,#E2E8F0); padding-top:0.5rem;'>"
        "관련 이벤트</div>",
        unsafe_allow_html=True,
    )

    try:
        from events.db import load_current_events
        evt_df, _ = load_current_events()
    except Exception:
        st.error("이벤트 데이터를 불러올 수 없습니다.")
        return

    if evt_df is None or len(evt_df) == 0:
        st.info("현재 운영 중인 이벤트가 없습니다.")
        return

    # 지점 필터
    filter_branches = selected_branches if selected_branches else []
    if branch_name and branch_name not in filter_branches:
        filter_branches = [branch_name] + filter_branches
    if filter_branches:
        evt_df = evt_df[evt_df["지점명"].isin(filter_branches)]
        branch_label = ", ".join(filter_branches)
    else:
        branch_label = "전체"

    # 키워드 추출: core_name + 매칭된 시술명 활용 (정확매칭 필터 전 전체)
    keywords = set()
    keywords.add(core_name)
    # 매칭된 시술명도 키워드에 추가 (써마지FLX → 써마지 이벤트 찾기)
    for name in all_matched_names:
        keywords.add(name)
    # DEVICE_ALIASES 역매핑 키워드 추가
    for canonical, aliases in DEVICE_ALIASES.items():
        for alias in aliases:
            if alias.lower() in core_name.lower() or core_name.lower() in alias.lower():
                keywords.add(canonical)
                keywords.update(aliases)
                break
    keywords = [kw for kw in keywords if len(kw) >= 2]

    mask = pd.Series(False, index=evt_df.index)
    for kw in keywords:
        mask = mask | evt_df["이벤트명"].str.contains(re.escape(kw), case=False, na=False)
    matched_evt = evt_df[mask]

    # 기간 표시
    period_label = ""
    if "기간" in evt_df.columns and len(evt_df) > 0:
        period_label = evt_df["기간"].dropna().unique()
        period_label = period_label[0] if len(period_label) > 0 else ""
    period_text = f" · 기간: {period_label}" if period_label else ""
    st.caption(f"지점: {branch_label} · 키워드: {', '.join(sorted(keywords))}{period_text}")

    if len(matched_evt) == 0:
        st.info(f"'{equip_name}' 관련 운영 중인 이벤트가 없습니다.")
        return

    st.markdown(f"**{len(matched_evt)}건** 매칭")

    display = matched_evt[["지점명", "카테고리", "이벤트명", "정상가", "이벤트가", "할인율", "비고"]].copy()
    display["정상가"] = display["정상가"].apply(lambda x: f"{int(x):,}" if pd.notna(x) and x else "-")
    display["이벤트가"] = display["이벤트가"].apply(lambda x: f"{int(x):,}" if pd.notna(x) and x else "-")
    display["할인율"] = display["할인율"].apply(lambda x: f"{x:.0f}%" if pd.notna(x) and x else "-")

    gb = GridOptionsBuilder.from_dataframe(display)
    gb.configure_column("지점명", header_name="지점", width=80, cellStyle={"textAlign": "center"})
    gb.configure_column("카테고리", width=90, cellStyle={"textAlign": "center"})
    gb.configure_column("이벤트명", width=250, flex=2)
    gb.configure_column("정상가", width=90, cellStyle={"textAlign": "right"})
    gb.configure_column("이벤트가", width=90, cellStyle={"textAlign": "right"})
    gb.configure_column("할인율", width=65, cellStyle={"textAlign": "center"})
    gb.configure_column("비고", width=150, flex=1, wrapText=True, autoHeight=True,
                        cellStyle={"lineHeight": "1.4", "whiteSpace": "normal", "wordBreak": "break-word"})
    gb.configure_default_column(sortable=True, filter=True, resizable=True)
    gb.configure_grid_options(domLayout="normal", headerHeight=32)

    AgGrid(
        display, gridOptions=gb.build(), custom_css=_aggrid_dark_css(),
        height=max(250, min(600, 32 + len(display) * 30)),
        update_mode=GridUpdateMode.NO_UPDATE,
        data_return_mode=DataReturnMode.AS_INPUT,
        fit_columns_on_grid_load=True, allow_unsafe_jscode=True, theme="streamlit",
        key="evt_dialog_grid",
    )


@st.fragment
def render_tab_equipment_list(filtered_df, df, selected_branches, permissions):
    if len(filtered_df) == 0:
        st.warning("선택한 조건에 해당하는 장비가 없습니다.")
        return

    # 저장 결과 메시지 표시
    if "save_result" in st.session_state:
        for msg in st.session_state.pop("save_result"):
            if msg.startswith("✅"):
                st.success(msg)
            elif msg.startswith("⚠️"):
                st.warning(msg)
            else:
                st.error(msg)

    # AG-Grid 데이터 준비
    grid_df = filtered_df[["순번", "지점명", "기기명", "카테고리", "사진유무", "수량", "비고"]].copy()
    grid_df = grid_df.reset_index(drop=True)

    can_edit = permissions["can_edit_photo"] and permissions["can_save"]

    if can_edit:
        grid_df["사진"] = grid_df["사진유무"].apply(lambda x: x == "있음")
    else:
        grid_df["사진"] = grid_df["사진유무"]

    gb = GridOptionsBuilder.from_dataframe(
        grid_df[["순번", "지점명", "기기명", "카테고리", "사진", "수량", "비고"]]
    )
    gb.configure_column("순번", header_name="No", width=60, cellStyle={"textAlign": "center"}, headerClass="ag-center-header")
    gb.configure_column("지점명", width=80, cellStyle={"textAlign": "center"}, headerClass="ag-center-header")
    if can_edit:
        # 더블클릭 = 편집 (AG-Grid 기본 동작), 원클릭 = 행 선택
        gb.configure_column("기기명", width=200, flex=2, editable=True,
                            cellStyle={"textAlign": "left", "cursor": "pointer"})
    else:
        gb.configure_column("기기명", width=200, flex=2)
    gb.configure_column("카테고리", width=90, cellStyle={"textAlign": "center"}, headerClass="ag-center-header")
    gb.configure_column("수량", width=60, cellStyle={"textAlign": "center"}, headerClass="ag-center-header")
    gb.configure_column("비고", width=200, flex=2, wrapText=True, autoHeight=True,
                        cellStyle={"lineHeight": "1.4", "whiteSpace": "normal", "wordBreak": "break-word"})

    if can_edit:
        gb.configure_column("사진", header_name="사진", width=70, editable=True,
                            cellRenderer="agCheckboxCellRenderer", cellEditor="agCheckboxCellEditor",
                            cellStyle={"textAlign": "center"}, headerClass="ag-center-header")
    else:
        gb.configure_column("사진", width=70, cellStyle={"textAlign": "center"}, headerClass="ag-center-header")

    gb.configure_default_column(sortable=True, filter=True, resizable=True)
    gb.configure_selection(selection_mode="single", use_checkbox=False)
    gb.configure_grid_options(domLayout="normal", headerHeight=32)

    # AG-Grid: JS가 뷰포트 기준으로 iframe 높이를 자동 계산
    st.markdown('<div class="equip-grid">', unsafe_allow_html=True)

    grid_response = AgGrid(
        grid_df[["순번", "지점명", "기기명", "카테고리", "사진", "수량", "비고"]],
        gridOptions=gb.build(), custom_css=_aggrid_dark_css(),
        height=500,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        data_return_mode=DataReturnMode.AS_INPUT if not can_edit else DataReturnMode.FILTERED_AND_SORTED,
        fit_columns_on_grid_load=True, allow_unsafe_jscode=True, theme="streamlit",
    )

    st.markdown("</div>", unsafe_allow_html=True)

    # ── 선택 정보 + 액션 버튼 ──
    selected_rows = grid_response.get("selected_rows", None)
    has_selection = selected_rows is not None and len(selected_rows) > 0
    edited_data = grid_response["data"]

    equip_name = ""
    branch_name = ""
    if has_selection:
        sel = selected_rows.iloc[0] if hasattr(selected_rows, "iloc") else selected_rows[0]
        equip_name = sel.get("기기명", "")
        branch_name = sel.get("지점명", "")

    # 선택 정보 바 (항상 공간 확보 — 클릭 시 높이 변동 방지)
    if has_selection:
        sel_html = (
            f"선택: <b>{branch_name}</b> · <b style=\"color:var(--accent,#2563EB);\">{equip_name}</b>"
        )
    else:
        sel_html = "<span style='color:var(--text-muted,#94A3B8);'>장비를 선택하세요</span>"
    st.markdown(
        f"<div style='background:var(--bg-card,#F8FAFC); border-left:3px solid var(--accent,#2563EB); "
        f"border-radius:4px; padding:0.35rem 0.75rem; margin:0.25rem 0; font-size:0.82rem; "
        f"color:var(--text-primary,#1E293B);'>{sel_html}</div>",
        unsafe_allow_html=True,
    )

    # 버튼 한 줄 배치: 조회 | 변경 저장 | CSV
    if can_edit:
        col_lookup, col_save, col_download = st.columns([1, 1, 1])
    else:
        col_lookup, col_download = st.columns([1, 1])

    with col_lookup:
        lookup_disabled = not has_selection
        if st.button("조회", type="primary", use_container_width=True,
                     key="btn_lookup", disabled=lookup_disabled):
            _show_lookup_dialog(equip_name, branch_name, selected_branches)

    if can_edit:
        with col_save:
            if st.button("변경 사항 저장", use_container_width=True):
                # 변경 감지를 저장 버튼 클릭 시에만 실행 (클릭마다 O(n) 방지)
                photo_changes = []
                name_changes = []
                for i in range(min(len(edited_data), len(grid_df))):
                    eq_id = int(filtered_df.iloc[i]["순번"])
                    orig_photo = grid_df.iloc[i]["사진"]
                    new_photo = edited_data.iloc[i]["사진"]
                    if new_photo != orig_photo:
                        photo_changes.append((eq_id, "O" if new_photo else ""))
                    orig_name = grid_df.iloc[i]["기기명"]
                    new_name = str(edited_data.iloc[i]["기기명"]).strip()
                    if new_name and new_name != orig_name:
                        name_changes.append((eq_id, new_name))
                total_changes = len(photo_changes) + len(name_changes)
                if total_changes > 0:
                    save_msgs = []
                    if photo_changes:
                        with st.spinner(f"사진 {len(photo_changes)}건 저장 중..."):
                            ok_count, errors = save_photo_changes(photo_changes)
                        if ok_count > 0:
                            save_msgs.append(f"사진 {ok_count}건 저장 완료")
                        for e in errors:
                            save_msgs.append(f"사진 오류: {e}")
                    if name_changes:
                        from equipment.db import update_equipment
                        name_ok = 0
                        for eq_id, new_name in name_changes:
                            try:
                                update_equipment(eq_id, name=new_name)
                                name_ok += 1
                            except Exception as e:
                                save_msgs.append(f"기기명 오류 ID {eq_id}: {e}")
                        if name_ok > 0:
                            save_msgs.append(f"기기명 {name_ok}건 저장 완료")
                    st.session_state["save_result"] = [f"✅ {m}" if "오류" not in m else f"❌ {m}" for m in save_msgs]
                    load_data.clear()
                    st.rerun(scope="app")
                else:
                    st.info("변경된 항목이 없습니다.")

    with col_download:
        csv_data = grid_df[["순번", "지점명", "기기명", "카테고리", "사진유무", "수량", "비고"]].to_csv(index=False).encode("utf-8-sig")
        st.download_button("CSV 다운로드", csv_data, "equipment_list.csv", "text/csv", use_container_width=True)




# ============================================================
# 탭 2: 장비 통합 검색
# ============================================================
def render_tab_search(filtered_df, df):
    if len(df) == 0:
        st.warning("데이터가 없습니다.")
        return

    st.subheader("장비 통합 검색")
    st.caption("유사한 이름의 장비를 하나의 그룹으로 묶어서 조회합니다.")

    all_groups = sorted(filtered_df["장비그룹"].unique())
    selected_group = st.selectbox("장비 그룹 선택", options=["전체"] + all_groups)

    if selected_group == "전체":
        group_summary = (
            filtered_df.groupby("장비그룹")
            .agg(보유지점수=("지점명", "nunique"), 총수량=("수량", "sum"), 카테고리=("카테고리", "first"))
            .sort_values("보유지점수", ascending=False)
            .reset_index()
        )
        group_summary.columns = ["장비그룹", "보유 지점 수", "총 수량", "카테고리"]

        st.dataframe(
            group_summary,
            use_container_width=True,
            height=min(700, max(400, 35 * len(group_summary) + 38)),
            column_config={
                "장비그룹": st.column_config.TextColumn("장비명 (통합)", width="large"),
                "보유 지점 수": st.column_config.NumberColumn("보유 지점 수", width="medium"),
                "총 수량": st.column_config.NumberColumn("총 수량", width="small"),
                "카테고리": st.column_config.TextColumn("카테고리", width="medium"),
            },
        )
    else:
        group_df = filtered_df[filtered_df["장비그룹"] == selected_group]

        has = len(group_df[group_df["사진유무"] == "있음"])
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.markdown(_kpi_card("🏢", "보유 지점 수", f"{group_df['지점명'].nunique()}", "var(--accent, #2563EB)"), unsafe_allow_html=True)
        with col_b:
            st.markdown(_kpi_card("📦", "총 수량", f"{int(group_df['수량'].sum())}", "var(--success, #059669)"), unsafe_allow_html=True)
        with col_c:
            st.markdown(_kpi_card("📷", "사진 보유율", f"{has}/{len(group_df)}", "var(--warning, #D97706)"), unsafe_allow_html=True)
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

        variants = group_df["기기명"].unique().tolist()
        if len(variants) > 1:
            st.info(f"이 그룹에 포함된 기기명 변형: {', '.join(variants)}")

        # 시술 사전 연동 — 장비명으로 시술 설명 매칭
        desc_map = get_treatment_descriptions([selected_group])
        if selected_group in desc_map:
            info = desc_map[selected_group]
            st.markdown(
                f"<div style='background:var(--bg-card, #f8fafc); border:1px solid var(--border, #e2e8f0); "
                f"border-left:4px solid var(--accent, #2563EB); border-radius:8px; padding:0.8rem 1rem; "
                f"margin-bottom:0.8rem;'>"
                f"<span style='font-size:0.75rem; color:var(--text-muted, #94A3B8); font-weight:600;'>📖 시술 정보</span><br>"
                f"<span style='font-size:0.9rem; color:var(--text-primary, #1E293B);'>"
                f"<b>{info['treatment']}</b> — {info['description']}</span></div>",
                unsafe_allow_html=True,
            )

        st.dataframe(
            group_df[["지점명", "기기명", "수량", "비고", "사진유무"]],
            use_container_width=True,
            column_config={
                "지점명": st.column_config.TextColumn("지점명", width="medium"),
                "기기명": st.column_config.TextColumn("기기명 (원본)", width="large"),
                "수량": st.column_config.NumberColumn("수량", width="small"),
                "비고": st.column_config.TextColumn("비고", width="large"),
                "사진유무": st.column_config.TextColumn("사진", width="small"),
            },
        )

        all_branch_set = set(df["지점명"].unique())
        has_branch_set = set(group_df["지점명"].unique())
        missing = sorted(all_branch_set - has_branch_set)
        if missing:
            with st.expander(f"미보유 지점 ({len(missing)}개)"):
                st.write(", ".join(missing))


# ============================================================
# 탭 3: 지점 비교
# ============================================================
def render_tab_compare(df, selected_branches):
    if len(df) == 0:
        st.warning("데이터가 없습니다.")
        return

    compare_default = selected_branches if selected_branches else []
    compare_branches = st.multiselect(
        "비교할 지점을 선택하세요 (2개 이상)",
        options=sorted(df["지점명"].unique()),
        default=compare_default,
        key="compare_branches",
    )

    if len(compare_branches) < 2:
        st.info("비교하려면 2개 이상의 지점을 선택해주세요.")
        return

    compare_df = df[df["지점명"].isin(compare_branches)]

    st.markdown("**지점별 카테고리 장비 수량 비교**")
    grouped = compare_df.groupby(["지점명", "카테고리"])["수량"].sum().reset_index()
    fig_compare = px.bar(
        grouped, x="카테고리", y="수량", color="지점명",
        barmode="group",
        color_discrete_sequence=["#2563EB", "#059669", "#D97706", "#DC2626", "#7C3AED", "#0891B2"],
    )
    fig_compare.update_layout(
        height=450, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=12, color="#64748B"),
        xaxis=dict(gridcolor="#E2E8F0"), yaxis=dict(gridcolor="#E2E8F0"),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(size=11), bgcolor="rgba(0,0,0,0)"),
    )
    fig_compare.update_traces(marker_cornerradius=4, marker_line_width=0)
    st.plotly_chart(fig_compare, use_container_width=True)

    st.markdown("**상세 비교 테이블**")
    pivot_compare = compare_df.pivot_table(
        index="지점명", columns="카테고리", values="수량", aggfunc="sum", fill_value=0,
    )
    pivot_compare["합계"] = pivot_compare.sum(axis=1)
    pivot_compare = pivot_compare.sort_values("합계", ascending=False)
    st.dataframe(pivot_compare, use_container_width=True)


# ============================================================
# 탭 4: 대시보드
# ============================================================
def render_tab_dashboard(permissions=None):
    """대시보드 — 홈 화면. 각 기능으로 이동하는 카드형 네비게이션."""
    if permissions is None:
        from auth import get_permissions
        permissions = get_permissions()

    st.markdown("""
    <div style="padding:0.5rem 0 1rem 0;">
        <h2 style="margin:0; font-weight:700; color:var(--text-primary);">유앤아이의원 통합 관리 시스템</h2>
        <p style="margin:0.25rem 0 0 0; color:var(--text-muted); font-size:0.85rem;">
            관리할 항목을 선택해주세요.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # 카드 데이터 정의
    cards = [
        {"title": "보유장비", "desc": "지점별 장비 현황 조회 및 관리", "menu": "보유장비", "color": "#2563EB"},
        {"title": "이벤트", "desc": "기간별 이벤트 목록 및 가격 비교", "menu": "이벤트", "color": "#059669"},
        {"title": "카페 마케팅", "desc": "카페 마케팅 현황 관리", "menu": "카페", "color": "#D97706"},
        {"title": "블로그 마케팅", "desc": "블로그 마케팅 현황 관리", "menu": "블로그", "color": "#7C3AED"},
        {"title": "가이드", "desc": "시스템 사용법 안내", "menu": "가이드", "color": "#64748B"},
    ]
    if permissions.get("can_manage_users", False):
        cards.append({"title": "사용자 관리", "desc": "계정 추가·역할 변경·삭제", "menu": "사용자 관리", "color": "#DC2626"})

    # 버튼을 카드처럼 스타일링 (CSS :has() 사용)
    st.markdown("""<style>
    .card-marker { display: none !important; }
    [data-testid="stVerticalBlockBorderWrapper"]:has(.card-marker) {
        margin-bottom: 0.75rem;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:has(.card-marker) .stButton button {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius, 10px) !important;
        padding: 1.2rem 1.25rem !important;
        min-height: 88px !important;
        text-align: left !important;
        box-shadow: var(--shadow-sm) !important;
        transition: all 0.2s ease !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:has(.card-marker) .stButton button:hover {
        box-shadow: var(--shadow-md) !important;
        transform: translateY(-2px);
        border-color: var(--accent) !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:has(.card-marker) .stButton button p {
        margin: 0 !important; text-align: left !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:has(.card-marker) .stButton button p:first-child {
        font-size: 1.05rem !important; font-weight: 700 !important;
        color: var(--text-primary) !important; margin-bottom: 0.35rem !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:has(.card-marker) .stButton button p:last-child {
        font-size: 0.78rem !important; font-weight: 400 !important;
        color: var(--text-muted) !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:has(.card-c-0) .stButton button { border-left: 4px solid #2563EB !important; }
    [data-testid="stVerticalBlockBorderWrapper"]:has(.card-c-1) .stButton button { border-left: 4px solid #059669 !important; }
    [data-testid="stVerticalBlockBorderWrapper"]:has(.card-c-2) .stButton button { border-left: 4px solid #D97706 !important; }
    [data-testid="stVerticalBlockBorderWrapper"]:has(.card-c-3) .stButton button { border-left: 4px solid #7C3AED !important; }
    [data-testid="stVerticalBlockBorderWrapper"]:has(.card-c-4) .stButton button { border-left: 4px solid #64748B !important; }
    [data-testid="stVerticalBlockBorderWrapper"]:has(.card-c-5) .stButton button { border-left: 4px solid #DC2626 !important; }
    </style>""", unsafe_allow_html=True)

    # 3열 그리드 — 버튼 자체가 카드 (클릭 시 탭 이동)
    cols = st.columns(3)
    for i, card in enumerate(cards):
        with cols[i % 3]:
            with st.container():
                st.markdown(f'<div class="card-marker card-c-{i}"></div>', unsafe_allow_html=True)
                label = f"**{card['title']}**\n\n{card['desc']}"
                if st.button(label, key=f"dash_goto_{card['menu']}",
                             use_container_width=True):
                    st.session_state["_goto_menu"] = card["menu"]
                    st.rerun()


# ============================================================
# 탭 5: 사용자 관리 (관리자 전용)
# ============================================================
def render_admin_panel():
    st.subheader("사용자 관리")
    ensure_memo_column()

    users = load_users()
    branches = get_branches()
    branch_map = {b["id"]: b["name"] for b in branches}
    current_user = st.session_state.get("username", "")
    other_users = [u["username"] for u in users if u["username"] != current_user]

    # ── 가로 레이아웃: 좌=관리 / 우=목록 ──
    col_mgmt, col_list = st.columns([3, 2])

    with col_list:
        st.markdown("**등록된 사용자**")
        if users:
            user_table = [{
                "ID": u["username"],
                "역할": ROLES.get(u["role"], {}).get("label", u["role"]),
                "지점": branch_map.get(u.get("branch_id"), "-"),
                "비고": u.get("memo", ""),
            } for u in users]
            st.dataframe(
                user_table, use_container_width=True, hide_index=True,
                height=min(35 * len(users) + 38, 450),
                column_config={
                    "ID": st.column_config.TextColumn("ID", width="small"),
                    "역할": st.column_config.TextColumn("역할", width="small"),
                    "지점": st.column_config.TextColumn("지점", width="small"),
                    "비고": st.column_config.TextColumn("비고", width="medium"),
                },
            )
        else:
            st.info("등록된 사용자가 없습니다.")

    with col_mgmt:
        tab_add, tab_role, tab_pw, tab_memo, tab_del, tab_sync, tab_dict = st.tabs(
            ["➕ 추가", "🔄 역할변경", "🔑 비밀번호", "📝 비고", "🗑️ 삭제", "📥 동기화", "📖 시술사전"]
        )

        # ── 사용자 추가 ──
        with tab_add:
            with st.form("add_user_form"):
                new_username = st.text_input("사용자 ID", key="add_uid")
                c1, c2 = st.columns(2)
                with c1:
                    new_password = st.text_input("비밀번호", type="password", key="add_pw")
                with c2:
                    new_password_confirm = st.text_input("비밀번호 확인", type="password", key="add_pw2")
                c3, c4 = st.columns(2)
                with c3:
                    new_role = st.selectbox(
                        "역할", options=["viewer", "branch", "editor", "admin"],
                        format_func=lambda r: ROLES[r]["label"], key="add_role",
                    )
                with c4:
                    branch_options = {b["id"]: b["name"] for b in branches}
                    new_branch_id = st.selectbox(
                        "담당 지점",
                        options=[None] + list(branch_options.keys()),
                        format_func=lambda x: "전 지점" if x is None else branch_options[x],
                        key="add_branch",
                    )
                new_memo = st.text_input("비고", key="add_memo", placeholder="사용자 식별 메모 (예: 홍길동 본사)")
                submitted = st.form_submit_button("추가", type="primary", use_container_width=True)
                if submitted:
                    if not new_username or not new_password:
                        st.error("ID와 비밀번호를 입력해주세요.")
                    elif len(new_username) < 2:
                        st.error("ID는 2자 이상이어야 합니다.")
                    elif new_password != new_password_confirm:
                        st.error("비밀번호가 일치하지 않습니다.")
                    elif new_role == "branch" and new_branch_id is None:
                        st.error("지점담당 역할은 담당 지점을 선택해야 합니다.")
                    else:
                        hashed = hash_password(new_password)
                        branch_id = new_branch_id if new_role == "branch" else None
                        ok, msg = add_user(new_username, hashed, new_role, branch_id, memo=new_memo)
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

        # ── 역할 변경 ──
        with tab_role:
            if not other_users:
                st.info("관리할 다른 사용자가 없습니다.")
            else:
                c1, c2, c3 = st.columns([2, 2, 1])
                with c1:
                    role_target = st.selectbox("대상", other_users, key="role_target")
                with c2:
                    role_new = st.selectbox(
                        "새 역할", options=["viewer", "editor", "admin"],
                        format_func=lambda r: ROLES[r]["label"], key="role_new",
                    )
                with c3:
                    st.markdown("<div style='height:1.6rem'></div>", unsafe_allow_html=True)
                    if st.button("변경", use_container_width=True, key="role_btn"):
                        ok, msg = update_user_role(role_target, role_new)
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

        # ── 비밀번호 초기화 ──
        with tab_pw:
            if not other_users:
                st.info("관리할 다른 사용자가 없습니다.")
            else:
                c1, c2, c3 = st.columns([2, 2, 1])
                with c1:
                    pw_target = st.selectbox("대상", other_users, key="pw_target")
                with c2:
                    pw_new = st.text_input("새 비밀번호", type="password", key="pw_new")
                with c3:
                    st.markdown("<div style='height:1.6rem'></div>", unsafe_allow_html=True)
                    if st.button("변경", use_container_width=True, key="pw_btn"):
                        if not pw_new:
                            st.error("새 비밀번호를 입력해주세요.")
                        else:
                            hashed = hash_password(pw_new)
                            ok, msg = update_user_password(pw_target, hashed)
                            if ok:
                                st.success(msg)
                            else:
                                st.error(msg)

        # ── 비고 수정 ──
        with tab_memo:
            all_usernames = [u["username"] for u in users]
            if not all_usernames:
                st.info("등록된 사용자가 없습니다.")
            else:
                memo_target = st.selectbox("대상", all_usernames, key="memo_target")
                current_memo = next((u.get("memo", "") for u in users if u["username"] == memo_target), "")
                memo_new = st.text_input("비고", value=current_memo, key="memo_new",
                                          placeholder="이 사용자에 대한 메모 (예: 홍길동 본사)")
                if st.button("저장", use_container_width=True, key="memo_btn"):
                    ok, msg = update_user_memo(memo_target, memo_new)
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

        # ── 사용자 삭제 ──
        with tab_del:
            if not other_users:
                st.info("관리할 다른 사용자가 없습니다.")
            else:
                c1, c2 = st.columns([3, 1])
                with c1:
                    del_target = st.selectbox("대상", other_users, key="del_target")
                    del_confirm = st.checkbox(f"'{del_target}' 삭제 확인", key="del_confirm")
                with c2:
                    st.markdown("<div style='height:1.6rem'></div>", unsafe_allow_html=True)
                    if st.button("삭제", type="primary", use_container_width=True, key="del_btn"):
                        if not del_confirm:
                            st.error("삭제 확인란을 체크해주세요.")
                        else:
                            ok, msg = remove_user(del_target)
                            if ok:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)

        # ── 데이터 동기화 ──
        with tab_sync:
            st.markdown("**장비 데이터 동기화**")
            st.caption("Google Sheets에서 최신 장비 데이터를 가져옵니다.")
            if st.button("장비 시트 동기화", type="primary", use_container_width=True, key="admin_eq_sync_btn"):
                from equipment.sync import sync_from_sheets
                with st.spinner("장비 동기화 중..."):
                    result = sync_from_sheets()
                st.success(f"완료: +{result['added']} ↻{result['updated']} ={result['skipped']}")
                load_data.clear()
                st.rerun()

            st.markdown("---")
            st.markdown("**이벤트 데이터 동기화**")
            from datetime import datetime
            now = datetime.now()
            _bm_idx = min((now.month - 1) // 2, 5)
            _pm = {0: (1, 2), 1: (3, 4), 2: (5, 6), 3: (7, 8), 4: (9, 10), 5: (11, 12)}
            sm, em = _pm[_bm_idx]
            evt_year = now.year
            st.caption(f"수집 기간: **{evt_year}년 {sm}-{em}월**")

            sync_method = st.radio(
                "동기화 방식", ["링크 입력", "파일 업로드"],
                horizontal=True, key="admin_evt_sync_method", label_visibility="collapsed",
            )
            if sync_method == "링크 입력":
                sheet_url = st.text_input(
                    "Google Sheets URL",
                    placeholder="https://docs.google.com/spreadsheets/d/...",
                    key="admin_evt_sheet_url",
                )
                st.caption("시트가 '링크가 있는 모든 사용자에게 공개'로 설정되어야 합니다.")
                if st.button("이벤트 수집 실행", type="primary", use_container_width=True, key="admin_evt_sync_url_btn"):
                    if not sheet_url:
                        st.error("URL을 입력해주세요.")
                    else:
                        from events.sync import run_event_sync_from_url
                        from events.db import load_current_events
                        with st.spinner("이벤트 수집 중..."):
                            result = run_event_sync_from_url(sheet_url, evt_year, sm, em)
                        if result["errors"]:
                            st.warning(f"수집 완료: {result['processed']}개 지점, "
                                       f"{result['total_items']:,}건 (오류 {len(result['errors'])}건)")
                            with st.expander("오류 상세"):
                                for err in result["errors"]:
                                    st.text(f"• {err}")
                        else:
                            st.success(f"수집 완료: {result['processed']}개 지점, {result['total_items']:,}건")
                        load_current_events.clear()
                        st.rerun()
            else:
                uploaded = st.file_uploader(
                    "Excel 파일 업로드", type=["xlsx", "xls"], key="admin_evt_file_upload",
                    help="각 시트 탭 이름이 지점명(예: 강남, 잠실)이어야 합니다.",
                )
                if uploaded is not None:
                    if st.button("이벤트 수집 실행", type="primary", use_container_width=True, key="admin_evt_sync_file_btn"):
                        from events.sync import run_event_sync_from_file
                        from events.db import load_current_events
                        with st.spinner("이벤트 수집 중..."):
                            result = run_event_sync_from_file(uploaded.read(), evt_year, sm, em)
                        if result["errors"]:
                            st.warning(f"수집 완료: {result['processed']}개 지점, "
                                       f"{result['total_items']:,}건 (오류 {len(result['errors'])}건)")
                        else:
                            st.success(f"수집 완료: {result['processed']}개 지점, {result['total_items']:,}건")
                        load_current_events.clear()
                        st.rerun()

            st.markdown("---")
            st.markdown("**카페 원고 데이터 가져오기**")
            from datetime import datetime as _dt_cafe
            _cafe_now = _dt_cafe.now()
            cafe_col1, cafe_col2, cafe_col3 = st.columns(3)
            with cafe_col1:
                cafe_year = st.number_input("연도", min_value=2024, max_value=2030,
                                             value=_cafe_now.year, key="admin_cafe_year")
            with cafe_col2:
                cafe_month = st.number_input("월", min_value=1, max_value=12,
                                              value=_cafe_now.month, key="admin_cafe_month")
            with cafe_col3:
                cafe_branch = st.text_input("지점 필터", value="동탄점", key="admin_cafe_branch",
                                             help="빈 칸이면 전체 지점")

            cafe_sheet_url = st.text_input(
                "카페 시트 URL (CAFE_SHEET_ID)",
                placeholder="Google Sheets URL 또는 환경변수에 CAFE_SHEET_ID 설정",
                key="admin_cafe_sheet_url",
            )
            if st.button("카페 원고 가져오기", type="primary", use_container_width=True, key="admin_cafe_sync_btn"):
                import os as _os_cafe
                if cafe_sheet_url.strip():
                    # URL에서 시트 ID 추출
                    import re as _re_cafe
                    _match = _re_cafe.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", cafe_sheet_url)
                    if _match:
                        _os_cafe.environ["CAFE_SHEET_ID"] = _match.group(1)
                    else:
                        _os_cafe.environ["CAFE_SHEET_ID"] = cafe_sheet_url.strip()

                from cafe.sync import run_cafe_import
                from cafe.db import load_cafe_articles
                with st.spinner("카페 원고 가져오는 중..."):
                    result = run_cafe_import(cafe_year, cafe_month, cafe_branch)
                if result["errors"]:
                    st.warning(f"완료: {result['processed']}개 지점, "
                               f"{result['total_articles']}건 (오류 {len(result['errors'])}건)")
                    with st.expander("오류 상세"):
                        for err in result["errors"]:
                            st.text(f"  {err}")
                else:
                    st.success(f"완료: {result['processed']}개 지점, {result['total_articles']}건")
                load_cafe_articles.clear()
                st.rerun()

        # ── 시술 사전 관리 ──
        with tab_dict:
            from equipment.db import (
                get_all_device_info, upsert_device_info, delete_device_info,
                update_device_usage_counts, seed_device_info_from_json,
            )

            st.markdown("**시술/장비 정보 사전 관리**")

            # 목록 표시
            all_devices = get_all_device_info()

            if all_devices:
                dict_df = pd.DataFrame(all_devices)
                display_cols = ["name", "category", "summary", "usage_count", "is_verified"]
                display_df = dict_df[display_cols].rename(columns={
                    "name": "시술명", "category": "카테고리", "summary": "설명",
                    "usage_count": "보유수", "is_verified": "검증",
                })
                display_df["검증"] = display_df["검증"].apply(lambda x: "✅" if x else "")

                st.dataframe(
                    display_df, use_container_width=True, hide_index=True,
                    height=min(35 * len(display_df) + 38, 350),
                    column_config={
                        "시술명": st.column_config.TextColumn("시술명", width="small"),
                        "카테고리": st.column_config.TextColumn("카테고리", width="small"),
                        "설명": st.column_config.TextColumn("설명", width="large"),
                        "보유수": st.column_config.NumberColumn("보유", width="small"),
                        "검증": st.column_config.TextColumn("검증", width="small"),
                    },
                )
                st.caption(f"총 {len(all_devices)}건 등록")
            else:
                st.info("등록된 시술 정보가 없습니다.")

            # 추가/수정 폼
            st.markdown("---")
            with st.expander("시술 정보 추가/수정", expanded=False):
                with st.form("dict_upsert_form"):
                    dict_name = st.text_input("시술명 *", key="dict_name",
                                              placeholder="예: 울쎄라피 프라임")
                    dc1, dc2 = st.columns(2)
                    with dc1:
                        dict_category = st.text_input("카테고리", key="dict_cat",
                                                       placeholder="예: 리프팅")
                    with dc2:
                        dict_aliases = st.text_input("별칭 (쉼표 구분)", key="dict_aliases",
                                                      placeholder="예: 울쎄라, 울쎄라프라임")
                    dict_summary = st.text_area("한줄 설명", key="dict_summary",
                                                 placeholder="초음파 열로 피부를 자극하는 리프팅 시술", height=68)
                    dict_target = st.text_input("적용 부위", key="dict_target",
                                                 placeholder="예: 얼굴 처짐, 턱선")
                    dict_mechanism = st.text_area("작용 원리", key="dict_mech",
                                                   placeholder="HIFU로 SMAS층까지 열에너지 전달", height=68)
                    dict_note = st.text_input("참고", key="dict_note",
                                               placeholder="추가 참고 사항")
                    if st.form_submit_button("저장", type="primary", use_container_width=True):
                        if not dict_name.strip():
                            st.error("시술명을 입력해주세요.")
                        else:
                            upsert_device_info(
                                name=dict_name.strip(),
                                category=dict_category.strip(),
                                summary=dict_summary.strip(),
                                target=dict_target.strip(),
                                mechanism=dict_mechanism.strip(),
                                note=dict_note.strip(),
                                aliases=dict_aliases.strip(),
                                is_verified=1,
                            )
                            st.success(f"'{dict_name.strip()}' 저장 완료")
                            st.rerun()

            # 삭제
            with st.expander("시술 정보 삭제", expanded=False):
                if all_devices:
                    device_names = [d["name"] for d in all_devices]
                    del_device = st.selectbox("삭제할 시술", device_names, key="dict_del_target")
                    del_device_confirm = st.checkbox(f"'{del_device}' 삭제 확인", key="dict_del_confirm")
                    if st.button("삭제", key="dict_del_btn", use_container_width=True):
                        if not del_device_confirm:
                            st.error("삭제 확인란을 체크해주세요.")
                        else:
                            delete_device_info(del_device)
                            st.success(f"'{del_device}' 삭제 완료")
                            st.rerun()
                else:
                    st.info("삭제할 시술 정보가 없습니다.")

            # 유틸리티
            with st.expander("유틸리티", expanded=False):
                uc1, uc2 = st.columns(2)
                with uc1:
                    if st.button("보유수 업데이트", use_container_width=True, key="dict_update_count"):
                        update_device_usage_counts()
                        st.success("보유수 업데이트 완료")
                        st.rerun()
                with uc2:
                    if st.button("JSON → DB 동기화", use_container_width=True, key="dict_seed"):
                        seed_device_info_from_json()
                        st.success("device_master.json 동기화 완료")
                        st.rerun()


# ============================================================
# 탭: 가이드
# ============================================================
def render_tab_guide():
    st.subheader("운영 가이드")
    st.caption("시스템 관리를 위한 절차 안내입니다.")

    with st.expander("메뉴 구조", expanded=False):
        st.markdown("""
| 메뉴 | 설명 | 접근 권한 |
|---|---|---|
| HOME | 대시보드 — 각 기능으로 이동하는 카드형 네비게이션 | 모두 |
| 보유장비 | 지점별 장비 현황 조회 및 사진 상태 관리 | 모두 |
| 이벤트 | 격월 이벤트 정보 조회, 검색, 비교 | 모두 |
| 카페 | 카페 마케팅 관리 (준비 중) | - |
| 블로그 | 블로그 마케팅 관리 (준비 중) | - |
| 가이드 | 시스템 사용 안내 | 모두 |
| 사용자 관리 | 계정/권한/동기화 관리 | 관리자 |
""")

    with st.expander("지점 필터 안내", expanded=False):
        st.markdown("""
**사이드바 지점 필터 (모든 탭 공통)**

- **뷰어/편집자/관리자**: 복수 지점 선택 가능 (미선택 시 전체 지점)
- **지점담당자**: 담당 지점만 자동 적용 (변경 불가)
- 선택한 지점 기준으로 모든 탭의 데이터가 필터링됩니다.
""")

    with st.expander("이벤트 탭 기능", expanded=False):
        st.markdown("""
**이벤트 탭 서브 뷰**

| 서브 뷰 | 설명 | 접근 권한 |
|---|---|---|
| 이벤트 목록 | 현재 기간 이벤트 목록 조회 및 필터링 | 모두 |
| 이벤트 검색 | 시술명/이벤트명으로 상세 검색 | 모두 |
| 지점 비교 | 지점별 이벤트 수 및 할인율 비교 | 편집자/관리자 |
| 기간별 가격 변동 | 동일 시술의 격월 단위 가격 변동 추적 | 모두 |
| 시술 사전 | 시술/장비 설명 조회 및 편집 | 편집자/관리자 편집 가능 |

**필터 기능:**
- 카테고리 선택, 이벤트명 검색
- 이벤트가 범위 필터 (최소 0원 ~ 최대 500만원, 직접 입력)
""")

    with st.expander("장비 데이터 동기화 안내", expanded=False):
        st.markdown("""
**Google Sheets → SQLite DB 동기화 규칙**

- 수동 실행: **사용자 관리** 탭 > **동기화** 탭에서 실행 (관리자 전용)

**동기화 규칙 (데이터 안전):**
1. 동기화 전 DB 자동 백업 (7일 보관)
2. Sheets에 있고 DB에 없는 행 → 새로 추가
3. Sheets에 있고 DB에도 있고 내용 동일 → 스킵
4. Sheets에 있고 DB에도 있고 내용 다름 → 로그만 남김 (덮어쓰지 않음)
5. DB에만 있는 행 (앱에서 추가한 것) → 유지
""")

    with st.expander("이벤트 동기화 안내", expanded=False):
        st.markdown("""
**이벤트 데이터 수집 (격월 단위)**

- **사용자 관리** 탭 > **동기화** 탭에서 실행 (관리자 전용)
- **링크 입력**: Google Sheets URL 붙여넣기 (시트 공개 설정 필요)
- **파일 업로드**: Excel 파일(.xlsx) 직접 업로드

**시트 구조 요구사항:**
- 각 시트 탭 이름 = 지점명 (예: 강남, 잠실, 부평 등)
- 탭 내부: 카테고리 → 이벤트명 | 정상가 | 이벤트가 | 비고

**수집 규칙:**
1. 같은 기간+지점 데이터가 이미 있으면 삭제 후 재수집 (최신 데이터 우선)
2. 카테고리 자동 매핑 (비표준 → 표준)
3. 매핑 실패 시 '기타'로 분류 + review_queue.json에 기록
""")

    with st.expander("장비 사진 관리", expanded=False):
        st.markdown("""
**사진 상태 변경 방법:**

1. 보유장비 탭 > '장비 목록'에서 사진 체크박스 클릭
2. '변경 사항 저장' 버튼 클릭 → DB에 즉시 반영
3. Google Sheets에는 반영되지 않음 (DB 우선 원칙)
""")

    with st.expander("사용자 권한 안내", expanded=False):
        st.markdown("""
| 역할 | 장비 조회 | 사진 편집 | 시술 사전 편집 | 동기화 | 사용자 관리 | 비고 |
|---|---|---|---|---|---|---|
| 뷰어 | ✅ | ❌ | ❌ | ❌ | ❌ | 전체 지점 읽기 전용 |
| 지점담당 | ✅ | ✅ | ❌ | ❌ | ❌ | 자기 지점만 조회/편집 |
| 편집자 | ✅ | ✅ | ✅ | ❌ | ❌ | 전체 지점 편집 + 시술 사전 |
| 관리자 | ✅ | ✅ | ✅ | ✅ | ✅ | 모든 권한 |

**사용자 관리 기능 (관리자 전용):**
- 사용자 추가: ID, 비밀번호, 역할, 담당 지점, 비고 등록
- 역할 변경 / 비밀번호 초기화
- 비고 관리: 사용자 식별용 메모 (예: 홍길동 본사)
- 데이터 동기화: 장비 및 이벤트 데이터 수집
""")


# ============================================================
# 탭: 이벤트 (events_ui 모듈에서 렌더링)
# ============================================================
def render_tab_events():
    from events.ui import render_tab_events as _render
    _render()


# ============================================================
# 탭: 카페 마케팅
# ============================================================
def render_tab_cafe():
    from cafe.ui import render_tab_cafe as _render
    _render()


# ============================================================
# 탭: 블로그 (placeholder)
# ============================================================
def render_tab_blog():
    st.subheader("블로그")
    st.info("곧 업데이트 됩니다.")
