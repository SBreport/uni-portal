"""카페 마케팅 탭 Streamlit UI 모듈.

서브 뷰: 대시보드 / 원고 목록 / 원고 작성
"""

import html as _html
import streamlit as st
import pandas as pd
from datetime import datetime

from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

from cafe.db import (
    STATUSES, STATUS_COLORS,
    load_cafe_periods, get_or_create_period,
    get_or_create_branch_period, load_branch_period_meta,
    update_branch_metadata,
    load_cafe_articles, load_cafe_article_detail,
    update_article, upsert_comment,
    add_feedback, change_status, set_published_info,
    load_status_history, load_cafe_summary,
    get_equipment_context,
)
from auth import get_permissions


# ── 공통 스타일 ──────────────────────────────────────────

def _aggrid_dark_css():
    return {
        ".ag-header": {"background-color": "#F8FAFC !important", "border-bottom": "2px solid #D97706 !important"},
        ".ag-header-cell": {"background-color": "#F8FAFC !important", "color": "#1E293B !important",
                            "padding": "0 6px !important", "font-weight": "600 !important"},
        ".ag-header-cell-label": {"justify-content": "center"},
        ".ag-cell": {"padding": "0 6px !important", "line-height": "28px !important"},
        ".ag-row": {"font-size": "13px"},
        ".ag-cell-wrapper": {"justify-content": "center"},
        ".ag-row-odd": {"background-color": "#FAFBFC !important"},
        ".ag-row-hover": {"background-color": "#FFF7ED !important"},
        ".ag-root-wrapper": {"border": "1px solid #E2E8F0 !important", "border-radius": "8px !important"},
        ":root.dark-theme .ag-cell": {"color": "#E0E0E0 !important", "border-color": "#2A2A4A !important"},
        ":root.dark-theme .ag-header": {"background-color": "#1E293B !important", "border-bottom": "2px solid #D97706 !important"},
        ":root.dark-theme .ag-header-cell": {"background-color": "#1E293B !important", "color": "#F1F5F9 !important"},
        ":root.dark-theme .ag-header-cell-label": {"color": "#F1F5F9 !important"},
        ":root.dark-theme .ag-row": {"background-color": "#0F172A !important", "color": "#E0E0E0 !important"},
        ":root.dark-theme .ag-root-wrapper": {"background-color": "#0F172A !important", "border-color": "#334155 !important"},
        ":root.dark-theme .ag-row-odd": {"background-color": "#1E293B !important"},
        ":root.dark-theme .ag-row-hover": {"background-color": "#2D1F0F !important"},
        ":root.dark-theme .ag-body-viewport": {"background-color": "#0F172A !important"},
    }


def _kpi_card(icon, label, value, color="#D97706"):
    return (
        f'<div style="background:var(--bg-card, #fff);border:1px solid var(--border, #E2E8F0);'
        f'border-left:4px solid {color};border-radius:10px;'
        f'padding:0.7rem 1rem;box-shadow:0 1px 2px rgba(0,0,0,0.05);height:100%;">'
        f'<div style="display:flex;align-items:center;gap:0.3rem;margin-bottom:0.2rem;">'
        f'<span style="font-size:1rem;">{icon}</span>'
        f'<span style="font-size:0.7rem;font-weight:600;color:var(--text-muted, #94A3B8);">{label}</span></div>'
        f'<div style="font-size:1.5rem;font-weight:700;color:var(--text-primary, #1E293B);line-height:1.2;">'
        f'{value}</div></div>'
    )


def _status_badge(status: str) -> str:
    color = STATUS_COLORS.get(status, "#6B7280")
    return f'<span style="background:{color};color:white;padding:2px 8px;border-radius:10px;font-size:12px;font-weight:600;">{status}</span>'


def _copy_btn_html(text: str, label: str) -> str:
    """JS 클립보드 복사 버튼 HTML 반환."""
    escaped = _html.escape(text or "", quote=True).replace("\n", "\\n").replace("'", "\\'")
    return (
        f'<button onclick="navigator.clipboard.writeText(\'{escaped}\'.replace(/\\\\n/g,\'\\n\'))'
        f'.then(()=>this.innerText=\'✅\').catch(()=>this.innerText=\'❌\');'
        f'setTimeout(()=>this.innerText=\'📋 {label}\',1200)"'
        f' style="background:none;border:1px solid var(--border, #CBD5E1);border-radius:6px;'
        f'padding:1px 7px;cursor:pointer;font-size:11px;color:var(--text-muted, #64748B);">'
        f'📋 {label}</button>'
    )


# ============================================================
# 메인 진입점
# ============================================================

def render_tab_cafe():
    _render_cafe_inner()


def _render_cafe_inner():
    permissions = get_permissions()
    now = datetime.now()

    # ── 상단 필터 바 ──
    col_f1, col_f2, col_f3 = st.columns([1.5, 1, 1.5])

    with col_f1:
        from events.db import load_evt_branches
        branches = load_evt_branches()
        branch_names = [b["name"] for b in branches]
        default_idx = branch_names.index("동탄점") if "동탄점" in branch_names else 0
        selected_branch = st.selectbox("지점", branch_names, index=default_idx, key="cafe_branch")
        branch_id = next((b["id"] for b in branches if b["name"] == selected_branch), None)

    with col_f2:
        selected_year = st.number_input("연도", min_value=2024, max_value=2030,
                                         value=now.year, key="cafe_year")
    with col_f3:
        selected_month = st.number_input("월", min_value=1, max_value=12,
                                          value=now.month, key="cafe_month")

    if not branch_id:
        st.error("지점을 선택해주세요.")
        return

    period_id = get_or_create_period(selected_year, selected_month)
    bp_id = get_or_create_branch_period(period_id, branch_id)

    # ── 서브 뷰 선택 ──
    sub_view = st.radio(
        "보기 선택", ["대시보드", "원고 목록", "원고 작성 v1", "원고 작성 v2"],
        horizontal=True, label_visibility="collapsed",
        key="cafe_sub_view",
    )

    if sub_view == "대시보드":
        _render_dashboard(period_id)
    elif sub_view == "원고 목록":
        _render_article_list(bp_id, selected_branch, permissions)
    elif sub_view == "원고 작성 v1":
        _render_article_edit(bp_id, selected_branch, permissions)
    elif sub_view == "원고 작성 v2":
        _render_article_edit_v2(bp_id, selected_branch, permissions)


# ============================================================
# 서브뷰 1: 대시보드 (전 지점 진행현황)
# ============================================================

@st.fragment
def _render_dashboard(period_id: int):
    summary = load_cafe_summary(period_id)

    if not summary:
        st.info("해당 월에 등록된 지점이 없습니다.")
        return

    # 전체 KPI
    total_all = sum(s.get("total_articles", 0) for s in summary)
    pub_all = sum(s.get("cnt_published", 0) for s in summary)
    wait_all = sum(s.get("cnt_waiting", 0) for s in summary)
    branches_total = len(summary)
    branches_done = sum(1 for s in summary
                        if s.get("total_articles", 0) > 0
                        and s.get("cnt_published", 0) == s.get("total_articles", 0))

    cols = st.columns(4)
    kpis = [
        ("📊", "전체 원고", f"{total_all}건", "#D97706"),
        ("🚀", "발행 완료", f"{pub_all}건", "#10B981"),
        ("📝", "미착수", f"{wait_all}건", "#6B7280"),
        ("🏥", "완료 지점", f"{branches_done}/{branches_total}", "#3B82F6"),
    ]
    for col, (icon, label, val, color) in zip(cols, kpis):
        col.markdown(_kpi_card(icon, label, val, color), unsafe_allow_html=True)

    st.markdown("")

    # 지점별 현황 AG Grid
    rows = []
    for s in summary:
        total = s.get("total_articles", 0)
        published = s.get("cnt_published", 0)
        progress = f"{published}/{total}" if total > 0 else "-"
        pct = int(published / total * 100) if total > 0 else 0
        rows.append({
            "지점": s["branch_name"],
            "담당자": s.get("smart_manager", "-") or "-",
            "원고작가": s.get("writer", "-") or "-",
            "총건수": total,
            "작성완료": s.get("cnt_written", 0),
            "검수완료": s.get("cnt_reviewed", 0),
            "발행완료": published,
            "수정요청": s.get("cnt_revision", 0),
            "진행률": pct,
        })

    if not rows:
        return

    dash_df = pd.DataFrame(rows)
    gb = GridOptionsBuilder.from_dataframe(dash_df)
    gb.configure_column("지점", width=90, pinned="left")
    gb.configure_column("담당자", width=80)
    gb.configure_column("원고작가", width=80)
    gb.configure_column("총건수", width=60)
    gb.configure_column("작성완료", width=70)
    gb.configure_column("검수완료", width=70)
    gb.configure_column("발행완료", width=70)
    gb.configure_column("수정요청", width=70)
    gb.configure_column("진행률", width=100,
                         cellRenderer=JsCode("""
                            function(params) {
                                var pct = params.value || 0;
                                var color = pct >= 100 ? '#10B981' : pct >= 50 ? '#F59E0B' : '#6B7280';
                                return '<div style="display:flex;align-items:center;gap:6px;">' +
                                    '<div style="flex:1;background:#E5E7EB;border-radius:4px;height:8px;">' +
                                    '<div style="width:' + pct + '%;background:' + color + ';height:100%;border-radius:4px;"></div></div>' +
                                    '<span style="font-size:11px;min-width:32px;">' + pct + '%</span></div>';
                            }
                         """))

    grid_options = gb.build()
    grid_options["custom_css"] = _aggrid_dark_css()

    AgGrid(
        dash_df,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.NO_UPDATE,
        height=min(400, 40 + len(rows) * 30),
        theme="streamlit",
        allow_unsafe_jscode=True,
    )


# ============================================================
# 서브뷰 2: 원고 목록 (순번, 장비, 제목, 상태, 링크)
# ============================================================

@st.fragment
def _render_article_list(bp_id: int, branch_name: str, permissions: dict):
    df = load_cafe_articles(bp_id)

    if len(df) == 0:
        st.info("등록된 원고가 없습니다.")
        if st.button("원고 20건 초기 생성", type="primary"):
            from cafe.db import upsert_article
            for i in range(1, 21):
                upsert_article(bp_id, i)
            load_cafe_articles.clear()
            st.rerun()
        return

    can_save = permissions.get("can_save", False)

    display_df = df.rename(columns={
        "article_order": "순번",
        "equipment_name": "장비",
        "title": "제목",
        "status": "상태",
        "published_url": "발행링크",
    })

    gb = GridOptionsBuilder.from_dataframe(
        display_df[["순번", "장비", "제목", "상태", "발행링크"]]
    )
    gb.configure_selection("single", use_checkbox=False)
    gb.configure_column("순번", width=60)
    gb.configure_column("장비", width=120, editable=can_save)
    gb.configure_column("제목", width=250, flex=1)
    gb.configure_column("상태", width=90,
                         cellStyle=JsCode("""
                            function(params) {
                                var colorMap = {
                                    '작성대기': '#6B7280', '작성완료': '#F59E0B',
                                    '수정요청': '#EF4444', '검수완료': '#3B82F6',
                                    '발행완료': '#10B981', '보류': '#8B5CF6'
                                };
                                var bg = colorMap[params.value] || '#6B7280';
                                return {
                                    'color': 'white', 'backgroundColor': bg,
                                    'borderRadius': '10px', 'textAlign': 'center',
                                    'fontWeight': '600', 'fontSize': '12px',
                                    'padding': '2px 4px', 'margin': '2px 0'
                                };
                            }
                         """))
    gb.configure_column("발행링크", width=60,
                         cellRenderer=JsCode("""
                            function(params) {
                                if (params.value) {
                                    return '<a href="' + params.value + '" target="_blank">🔗</a>';
                                }
                                return '';
                            }
                         """))

    grid_options = gb.build()
    grid_options["custom_css"] = _aggrid_dark_css()

    update_mode = GridUpdateMode.VALUE_CHANGED if can_save else GridUpdateMode.SELECTION_CHANGED

    grid_response = AgGrid(
        display_df[["id", "순번", "장비", "제목", "상태", "발행링크"]],
        gridOptions=grid_options,
        update_mode=update_mode,
        height=500,
        theme="streamlit",
        allow_unsafe_jscode=True,
    )

    # 장비 인라인 수정 반영
    if can_save and grid_response.get("data") is not None:
        updated_df = grid_response["data"]
        for _, row in updated_df.iterrows():
            orig = df[df["id"] == row["id"]]
            if len(orig) > 0:
                orig_equip = orig.iloc[0].get("equipment_name", "") or ""
                new_equip = row.get("장비", "") or ""
                if new_equip != orig_equip:
                    update_article(int(row["id"]), equipment_name=new_equip)

    # 행 선택 시 원고 작성으로 이동
    selected = grid_response.get("selected_rows", None)
    if selected is not None and len(selected) > 0:
        if isinstance(selected, pd.DataFrame):
            sel_id = int(selected.iloc[0]["id"])
        else:
            sel_id = int(selected[0]["id"])
        st.session_state["cafe_selected_article_id"] = sel_id
        st.session_state["cafe_sub_view"] = "원고 작성 v1"
        st.rerun()


# ============================================================
# 서브뷰 3: 원고 작성 (모바일 규격 입력)
# ============================================================

def _render_article_edit(bp_id: int, branch_name: str, permissions: dict):
    # 원고 목록 로드 (이전/다음 네비게이션용)
    df = load_cafe_articles(bp_id)
    if len(df) == 0:
        st.info("원고가 없습니다. 원고 목록에서 초기 생성을 해주세요.")
        return

    article_id = st.session_state.get("cafe_selected_article_id")
    article_ids = df["id"].tolist()
    article_orders = df["article_order"].tolist()
    article_titles = df["title"].tolist()

    if not article_id or article_id not in article_ids:
        article_id = article_ids[0]
        st.session_state["cafe_selected_article_id"] = article_id

    current_idx = article_ids.index(article_id)

    # ── 공통 CSS ──
    st.markdown("""<style>
    .copy-icon {
        display:inline-block; cursor:pointer;
        font-size:14px; color:var(--text-muted, #94A3B8);
        vertical-align:middle; margin-left:4px;
    }
    .copy-icon:hover { color:var(--text-primary, #1E293B); }
    .copy-icon:active { transform:scale(0.9); }
    [data-testid="stTextArea"]:has(textarea[aria-label="본문"]) textarea {
        font-size: 14px !important;
        line-height: 1.8 !important;
        letter-spacing: -0.01em !important;
    }
    </style>""", unsafe_allow_html=True)

    detail = load_cafe_article_detail(article_id)
    if not detail:
        st.error("원고를 찾을 수 없습니다.")
        return

    can_save = permissions.get("can_save", False)
    username = st.session_state.get("username", "")
    current_status = detail.get("status", "작성대기")

    # ━━━ ROW 1: 네비게이션 | (빈칸) | (빈칸) ━━━
    r1_left, r1_mid, r1_right = st.columns([3, 3, 3])
    with r1_left:
        nav_p, nav_t, nav_n = st.columns([1, 3, 1])
        with nav_p:
            if current_idx > 0:
                if st.button(f"◀#{article_orders[current_idx - 1]}", key="cafe_nav_prev"):
                    st.session_state["cafe_selected_article_id"] = article_ids[current_idx - 1]
                    st.rerun()
        with nav_t:
            st.markdown(
                f'<div style="text-align:center;font-weight:700;font-size:14px;padding:6px 0;'
                f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">'
                f'#{article_orders[current_idx]} '
                f'{_html.escape(article_titles[current_idx] or "(미작성)")}</div>',
                unsafe_allow_html=True,
            )
        with nav_n:
            if current_idx < len(article_ids) - 1:
                if st.button(f"#{article_orders[current_idx + 1]}▶", key="cafe_nav_next"):
                    st.session_state["cafe_selected_article_id"] = article_ids[current_idx + 1]
                    st.rerun()
    # r1_mid, r1_right: 의도적으로 비워둠

    # ━━━ ROW 2: 키워드/카테/장비 | 진행상황 | 원고링크+저장 ━━━
    r2_left, r2_mid, r2_right = st.columns([3, 3, 3])
    with r2_left:
        kc1, kc2, kc3 = st.columns(3)
        with kc1:
            keyword = st.text_input("키워드", value=detail.get("keyword", ""),
                                     disabled=not can_save, key="cafe_edit_keyword")
        with kc2:
            category = st.text_input("카테고리", value=detail.get("category", ""),
                                      disabled=not can_save, key="cafe_edit_category")
        with kc3:
            equipment = st.text_input("장비", value=detail.get("equipment_name", ""),
                                       disabled=not can_save, key="cafe_edit_equipment")
    with r2_mid:
        st.markdown(
            f'<div style="border:1px solid var(--border, #E2E8F0);border-radius:10px;'
            f'padding:0.6rem 0.8rem;">'
            f'<span style="font-weight:600;font-size:13px;">진행 상황</span> '
            f'{_status_badge(current_status)}</div>',
            unsafe_allow_html=True,
        )
        if can_save:
            cs1, cs2 = st.columns([2, 1])
            with cs1:
                new_status = st.selectbox(
                    "변경", STATUSES,
                    index=STATUSES.index(current_status) if current_status in STATUSES else 0,
                    key="cafe_new_status", label_visibility="collapsed",
                )
            with cs2:
                if st.button("변경", key="cafe_change_status"):
                    if new_status != current_status:
                        change_status(article_id, new_status, changed_by=username, note="")
                        load_cafe_articles.clear()
                        st.rerun()
    with r2_right:
        pub_url = st.text_input("발행 URL", value=detail.get("published_url", ""),
                                 disabled=not can_save, key="cafe_pub_url",
                                 placeholder="https://cafe.naver.com/...")
        if can_save and st.button("발행 URL 저장", key="cafe_save_pub_url",
                                   use_container_width=True):
            if pub_url.strip():
                set_published_info(article_id, pub_url.strip(), username)
                load_cafe_articles.clear()
                st.rerun()

    st.markdown("---")

    # ━━━ ROW 3: 제목+본문 | 댓글 | 피드백 (동일 3분할) ━━━
    col_body, col_comments, col_side = st.columns([3, 3, 3])

    # ━━━ 좌: 제목 + 본문 (복사 아이콘은 라벨 옆 인라인) ━━━
    with col_body:
        _t_js = _html.escape(detail.get("title", "") or "", quote=True).replace("'", "\\'")
        _b_js_default = _html.escape(detail.get("body", "") or "", quote=True).replace("\n", "\\n").replace("'", "\\'")
        # 제목 라벨 + 복사 아이콘 인라인
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:0px;">'
            f'<span style="font-size:13px;font-weight:600;">제목</span>'
            f'<span class="copy-icon" id="copy_title" title="제목 복사" onclick="'
            f"var el=document.querySelector('input[aria-label=\\'제목\\']');"
            f"if(el)navigator.clipboard.writeText(el.value)"
            f'.then(()=>document.getElementById(\'copy_title\').innerText=\'✅\')'
            f'.catch(()=>document.getElementById(\'copy_title\').innerText=\'❌\');'
            f'setTimeout(()=>document.getElementById(\'copy_title\').innerText=\'📄\',1000)'
            f'">📄</span></div>',
            unsafe_allow_html=True,
        )
        title = st.text_input("제목", value=detail.get("title", ""),
                               disabled=not can_save, key="cafe_edit_title",
                               label_visibility="collapsed",
                               placeholder="카페 게시글 제목")

        # 본문 라벨 + 복사 아이콘 인라인
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:0px;">'
            f'<span style="font-size:13px;font-weight:600;">본문</span>'
            f'<span class="copy-icon" id="copy_body" title="본문 복사" onclick="'
            f"var el=document.querySelector('textarea[aria-label=\\'본문\\']');"
            f"if(el)navigator.clipboard.writeText(el.value)"
            f'.then(()=>document.getElementById(\'copy_body\').innerText=\'✅\')'
            f'.catch(()=>document.getElementById(\'copy_body\').innerText=\'❌\');'
            f'setTimeout(()=>document.getElementById(\'copy_body\').innerText=\'📄\',1000)'
            f'">📄</span></div>',
            unsafe_allow_html=True,
        )
        body = st.text_area("본문", value=detail.get("body", ""),
                             height=500, disabled=not can_save, key="cafe_edit_body",
                             label_visibility="collapsed",
                             placeholder="카페 바이럴 원고 본문을 작성하세요")

    # ━━━ 중: 댓글 / 대댓글 ━━━
    with col_comments:
        comments_data = {c["slot_number"]: c for c in detail.get("comments", [])}
        max_existing = max(comments_data.keys()) if comments_data else 0
        default_slots = max(3, max_existing)
        slot_key = f"cafe_comment_slots_{article_id}"
        if slot_key not in st.session_state:
            st.session_state[slot_key] = default_slots
        num_slots = st.session_state[slot_key]

        ch1, ch2 = st.columns([2, 1])
        with ch1:
            st.markdown(f"**댓글** ({num_slots})")
        with ch2:
            if num_slots < 10:
                if st.button("➕", key="cafe_add_comment_slot"):
                    st.session_state[slot_key] = num_slots + 1
                    st.rerun()

        comment_edits = []
        for slot in range(1, num_slots + 1):
            existing = comments_data.get(slot, {})
            ct = st.text_area(
                f"💬 댓글 {slot}", value=existing.get("comment_text", ""),
                height=60, disabled=not can_save,
                key=f"cafe_comment_{slot}",
            )
            _ct_js = _html.escape(ct or "", quote=True).replace("\n", "\\n").replace("'", "\\'")
            rt = st.text_area(
                f"↳ 대댓글 {slot}", value=existing.get("reply_text", ""),
                height=60, disabled=not can_save,
                key=f"cafe_reply_{slot}",
            )
            _rt_js = _html.escape(rt or "", quote=True).replace("\n", "\\n").replace("'", "\\'")
            # 복사 아이콘 (댓글+대댓글 한 줄)
            st.markdown(
                f'<span class="copy-icon" title="댓글{slot} 복사" onclick="navigator.clipboard.writeText(\'{_ct_js}\'.replace(/\\\\n/g,\'\\n\'))'
                f'.then(()=>this.innerText=\'✅\').catch(()=>this.innerText=\'❌\');'
                f'setTimeout(()=>this.innerText=\'📄\',1000)">📄</span>'
                f'<span style="font-size:11px;color:var(--text-muted,#94A3B8);margin:0 4px;">댓{slot}</span>'
                f'<span class="copy-icon" title="대댓글{slot} 복사" onclick="navigator.clipboard.writeText(\'{_rt_js}\'.replace(/\\\\n/g,\'\\n\'))'
                f'.then(()=>this.innerText=\'✅\').catch(()=>this.innerText=\'❌\');'
                f'setTimeout(()=>this.innerText=\'📄\',1000)">📄</span>'
                f'<span style="font-size:11px;color:var(--text-muted,#94A3B8);">대댓{slot}</span>',
                unsafe_allow_html=True,
            )
            comment_edits.append((slot, ct, rt))

    # ━━━ 우: 피드백 전용 ━━━
    with col_side:
        st.markdown("**📋 피드백**")
        feedbacks = detail.get("feedbacks", [])
        if feedbacks:
            fb_html = '<div style="max-height:400px;overflow-y:auto;padding-right:4px;">'
            for fb in feedbacks:
                date_str = fb["created_at"][:10] if fb.get("created_at") else ""
                fb_html += (
                    f'<div style="background:var(--bg-card, #F8FAFC);border:1px solid var(--border, #E2E8F0);'
                    f'border-radius:8px;padding:0.6rem;margin-bottom:0.4rem;">'
                    f'<div style="font-size:11px;color:var(--text-muted, #94A3B8);margin-bottom:3px;">'
                    f'{_html.escape(fb["author"])} - {date_str}</div>'
                    f'<div style="font-size:13px;">{_html.escape(fb["content"])}</div></div>'
                )
            fb_html += '</div>'
            st.markdown(fb_html, unsafe_allow_html=True)
        else:
            st.caption("피드백 없음")

        if can_save:
            new_feedback = st.text_area("피드백 작성", height=150, key="cafe_new_feedback",
                                         label_visibility="collapsed",
                                         placeholder="수정 요청이나 승인 의견을 입력하세요")
            if st.button("피드백 등록", key="cafe_submit_feedback", use_container_width=True):
                if new_feedback.strip():
                    add_feedback(article_id, username, new_feedback.strip())
                    load_cafe_articles.clear()
                    st.rerun()

        with st.expander("상태 변경 이력", expanded=False):
            history = load_status_history(article_id)
            if history:
                for h in history[:10]:
                    date_str = h["changed_at"][:16] if h.get("changed_at") else ""
                    st.caption(f"{date_str} | {h['old_status']} -> {h['new_status']} | {h.get('changed_by', '')}")
            else:
                st.caption("이력 없음")

    # ━━━ 3열 아래: 저장 버튼 (전체 폭) ━━━
    if can_save:
        if st.button("💾 저장", type="primary", use_container_width=True,
                      key="cafe_save_article"):
            update_article(
                article_id,
                title=title, body=body,
                keyword=keyword, category=category,
                equipment_name=equipment,
            )
            for slot, ct, rt in comment_edits:
                upsert_comment(article_id, slot, ct, rt)
            load_cafe_articles.clear()
            st.success("저장 완료!")
            st.rerun()


# ============================================================
# 서브뷰 3-v2: 원고 작성 v2 (스타일 비교용, v1과 동일 기능)
# ============================================================

def _render_article_edit_v2(bp_id: int, branch_name: str, permissions: dict):
    """원고 작성 v2 — v1과 동일 기능, 레이아웃 실험용."""
    df = load_cafe_articles(bp_id)
    if len(df) == 0:
        st.info("원고가 없습니다. 원고 목록에서 초기 생성을 해주세요.")
        return

    article_id = st.session_state.get("cafe_selected_article_id")
    article_ids = df["id"].tolist()
    article_orders = df["article_order"].tolist()
    article_titles = df["title"].tolist()

    if not article_id or article_id not in article_ids:
        article_id = article_ids[0]
        st.session_state["cafe_selected_article_id"] = article_id

    current_idx = article_ids.index(article_id)

    # ── 공통 CSS ──
    st.markdown("""<style>
    .copy-icon-v2 {
        display:inline-block; cursor:pointer;
        font-size:14px; color:var(--text-muted, #94A3B8);
        vertical-align:middle; margin-left:4px;
    }
    .copy-icon-v2:hover { color:var(--text-primary, #1E293B); }
    .copy-icon-v2:active { transform:scale(0.9); }
    [data-testid="stTextArea"]:has(textarea[aria-label="본문v2"]) textarea {
        font-size: 14px !important;
        line-height: 1.8 !important;
        letter-spacing: -0.01em !important;
    }
    </style>""", unsafe_allow_html=True)

    detail = load_cafe_article_detail(article_id)
    if not detail:
        st.error("원고를 찾을 수 없습니다.")
        return

    can_save = permissions.get("can_save", False)
    username = st.session_state.get("username", "")
    current_status = detail.get("status", "작성대기")

    # ━━━ ROW 1: 네비게이션 | (빈칸) | (빈칸) ━━━
    r1_left, r1_mid, r1_right = st.columns([3, 3, 3])
    with r1_left:
        nav_p, nav_t, nav_n = st.columns([1, 3, 1])
        with nav_p:
            if current_idx > 0:
                if st.button(f"◀#{article_orders[current_idx - 1]}", key="v2_nav_prev"):
                    st.session_state["cafe_selected_article_id"] = article_ids[current_idx - 1]
                    st.rerun()
        with nav_t:
            st.markdown(
                f'<div style="text-align:center;font-weight:700;font-size:14px;padding:6px 0;'
                f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">'
                f'#{article_orders[current_idx]} '
                f'{_html.escape(article_titles[current_idx] or "(미작성)")}</div>',
                unsafe_allow_html=True,
            )
        with nav_n:
            if current_idx < len(article_ids) - 1:
                if st.button(f"#{article_orders[current_idx + 1]}▶", key="v2_nav_next"):
                    st.session_state["cafe_selected_article_id"] = article_ids[current_idx + 1]
                    st.rerun()

    # ━━━ ROW 2: 키워드/카테/장비 | 진행상황 | 원고링크+저장 ━━━
    r2_left, r2_mid, r2_right = st.columns([3, 3, 3])
    with r2_left:
        kc1, kc2, kc3 = st.columns(3)
        with kc1:
            keyword = st.text_input("키워드", value=detail.get("keyword", ""),
                                     disabled=not can_save, key="v2_edit_keyword")
        with kc2:
            category = st.text_input("카테고리", value=detail.get("category", ""),
                                      disabled=not can_save, key="v2_edit_category")
        with kc3:
            equipment = st.text_input("장비", value=detail.get("equipment_name", ""),
                                       disabled=not can_save, key="v2_edit_equipment")
    with r2_mid:
        st.markdown(
            f'<div style="border:1px solid var(--border, #E2E8F0);border-radius:10px;'
            f'padding:0.6rem 0.8rem;">'
            f'<span style="font-weight:600;font-size:13px;">진행 상황</span> '
            f'{_status_badge(current_status)}</div>',
            unsafe_allow_html=True,
        )
        if can_save:
            cs1, cs2 = st.columns([2, 1])
            with cs1:
                new_status = st.selectbox(
                    "변경", STATUSES,
                    index=STATUSES.index(current_status) if current_status in STATUSES else 0,
                    key="v2_new_status", label_visibility="collapsed",
                )
            with cs2:
                if st.button("변경", key="v2_change_status"):
                    if new_status != current_status:
                        change_status(article_id, new_status, changed_by=username, note="")
                        load_cafe_articles.clear()
                        st.rerun()
    with r2_right:
        pub_url = st.text_input("발행 URL", value=detail.get("published_url", ""),
                                 disabled=not can_save, key="v2_pub_url",
                                 placeholder="https://cafe.naver.com/...")
        if can_save and st.button("발행 URL 저장", key="v2_save_pub_url",
                                   use_container_width=True):
            if pub_url.strip():
                set_published_info(article_id, pub_url.strip(), username)
                load_cafe_articles.clear()
                st.rerun()

    st.markdown("---")

    # ━━━ ROW 3: 제목+본문 | 댓글 | 피드백 ━━━
    col_body, col_comments, col_side = st.columns([3, 3, 3])

    with col_body:
        st.markdown(
            '<div style="display:flex;align-items:center;gap:6px;margin-bottom:0px;">'
            '<span style="font-size:13px;font-weight:600;">제목</span>'
            '<span class="copy-icon-v2" id="v2_copy_title" title="제목 복사" onclick="'
            "var el=document.querySelector('input[aria-label=\\'제목v2\\']');"
            "if(el)navigator.clipboard.writeText(el.value)"
            ".then(()=>document.getElementById('v2_copy_title').innerText='✅')"
            ".catch(()=>document.getElementById('v2_copy_title').innerText='❌');"
            "setTimeout(()=>document.getElementById('v2_copy_title').innerText='📄',1000)"
            '">📄</span></div>',
            unsafe_allow_html=True,
        )
        title = st.text_input("제목v2", value=detail.get("title", ""),
                               disabled=not can_save, key="v2_edit_title",
                               label_visibility="collapsed",
                               placeholder="카페 게시글 제목")

        st.markdown(
            '<div style="display:flex;align-items:center;gap:6px;margin-bottom:0px;">'
            '<span style="font-size:13px;font-weight:600;">본문</span>'
            '<span class="copy-icon-v2" id="v2_copy_body" title="본문 복사" onclick="'
            "var el=document.querySelector('textarea[aria-label=\\'본문v2\\']');"
            "if(el)navigator.clipboard.writeText(el.value)"
            ".then(()=>document.getElementById('v2_copy_body').innerText='✅')"
            ".catch(()=>document.getElementById('v2_copy_body').innerText='❌');"
            "setTimeout(()=>document.getElementById('v2_copy_body').innerText='📄',1000)"
            '">📄</span></div>',
            unsafe_allow_html=True,
        )
        body = st.text_area("본문v2", value=detail.get("body", ""),
                             height=500, disabled=not can_save, key="v2_edit_body",
                             label_visibility="collapsed",
                             placeholder="카페 바이럴 원고 본문을 작성하세요")

    with col_comments:
        comments_data = {c["slot_number"]: c for c in detail.get("comments", [])}
        max_existing = max(comments_data.keys()) if comments_data else 0
        default_slots = max(3, max_existing)
        slot_key = f"v2_comment_slots_{article_id}"
        if slot_key not in st.session_state:
            st.session_state[slot_key] = default_slots
        num_slots = st.session_state[slot_key]

        ch1, ch2 = st.columns([2, 1])
        with ch1:
            st.markdown(f"**댓글** ({num_slots})")
        with ch2:
            if num_slots < 10:
                if st.button("➕", key="v2_add_comment"):
                    st.session_state[slot_key] = num_slots + 1
                    st.rerun()

        comment_edits = []
        for slot in range(1, num_slots + 1):
            existing = comments_data.get(slot, {})
            ct = st.text_area(
                f"💬 댓글 {slot}", value=existing.get("comment_text", ""),
                height=60, disabled=not can_save,
                key=f"v2_comment_{slot}",
            )
            _ct_js = _html.escape(ct or "", quote=True).replace("\n", "\\n").replace("'", "\\'")
            rt = st.text_area(
                f"↳ 대댓글 {slot}", value=existing.get("reply_text", ""),
                height=60, disabled=not can_save,
                key=f"v2_reply_{slot}",
            )
            _rt_js = _html.escape(rt or "", quote=True).replace("\n", "\\n").replace("'", "\\'")
            st.markdown(
                f'<span class="copy-icon-v2" title="댓글{slot}" onclick="navigator.clipboard.writeText(\'{_ct_js}\'.replace(/\\\\n/g,\'\\n\'))'
                f'.then(()=>this.innerText=\'✅\').catch(()=>this.innerText=\'❌\');'
                f'setTimeout(()=>this.innerText=\'📄\',1000)">📄</span>'
                f'<span style="font-size:11px;color:var(--text-muted,#94A3B8);margin:0 4px;">댓{slot}</span>'
                f'<span class="copy-icon-v2" title="대댓글{slot}" onclick="navigator.clipboard.writeText(\'{_rt_js}\'.replace(/\\\\n/g,\'\\n\'))'
                f'.then(()=>this.innerText=\'✅\').catch(()=>this.innerText=\'❌\');'
                f'setTimeout(()=>this.innerText=\'📄\',1000)">📄</span>'
                f'<span style="font-size:11px;color:var(--text-muted,#94A3B8);">대댓{slot}</span>',
                unsafe_allow_html=True,
            )
            comment_edits.append((slot, ct, rt))

    with col_side:
        st.markdown("**📋 피드백**")
        feedbacks = detail.get("feedbacks", [])
        if feedbacks:
            fb_html = '<div style="max-height:400px;overflow-y:auto;padding-right:4px;">'
            for fb in feedbacks:
                date_str = fb["created_at"][:10] if fb.get("created_at") else ""
                fb_html += (
                    f'<div style="background:var(--bg-card, #F8FAFC);border:1px solid var(--border, #E2E8F0);'
                    f'border-radius:8px;padding:0.6rem;margin-bottom:0.4rem;">'
                    f'<div style="font-size:11px;color:var(--text-muted, #94A3B8);margin-bottom:3px;">'
                    f'{_html.escape(fb["author"])} - {date_str}</div>'
                    f'<div style="font-size:13px;">{_html.escape(fb["content"])}</div></div>'
                )
            fb_html += '</div>'
            st.markdown(fb_html, unsafe_allow_html=True)
        else:
            st.caption("피드백 없음")

        if can_save:
            new_feedback = st.text_area("피드백 작성", height=150, key="v2_new_feedback",
                                         label_visibility="collapsed",
                                         placeholder="수정 요청이나 승인 의견을 입력하세요")
            if st.button("피드백 등록", key="v2_submit_feedback", use_container_width=True):
                if new_feedback.strip():
                    add_feedback(article_id, username, new_feedback.strip())
                    load_cafe_articles.clear()
                    st.rerun()

        with st.expander("상태 변경 이력", expanded=False):
            history = load_status_history(article_id)
            if history:
                for h in history[:10]:
                    date_str = h["changed_at"][:16] if h.get("changed_at") else ""
                    st.caption(f"{date_str} | {h['old_status']} -> {h['new_status']} | {h.get('changed_by', '')}")
            else:
                st.caption("이력 없음")

    # 저장 버튼
    if can_save:
        if st.button("💾 저장", type="primary", use_container_width=True,
                      key="v2_save_article"):
            update_article(
                article_id,
                title=title, body=body,
                keyword=keyword, category=category,
                equipment_name=equipment,
            )
            for slot, ct, rt in comment_edits:
                upsert_comment(article_id, slot, ct, rt)
            load_cafe_articles.clear()
            st.success("저장 완료!")
            st.rerun()
