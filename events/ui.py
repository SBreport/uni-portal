"""이벤트 탭 Streamlit UI 모듈.

서브 뷰: 이벤트 목록 / 이벤트 검색 / 지점 비교 / 가격 이력
"""

import streamlit as st
import pandas as pd
import plotly.express as px

from events.db import (
    load_current_events,
    load_evt_branches,
    load_evt_categories,
    load_event_summary,
    load_price_history,
    search_by_treatment,
    load_treatment_list,
    load_treatment_dictionary,
    update_treatment_info,
    add_treatment_entry,
)
from auth import get_permissions


def _format_price(val):
    """가격을 천 단위 콤마 형식으로 변환."""
    if pd.isna(val) or val is None:
        return "-"
    return f"{int(val):,}"


def render_tab_events():
    """이벤트 관리 탭 — 서브 뷰 전환."""
    sub_view = st.radio(
        "보기 선택", ["이벤트 목록", "이벤트 검색", "지점 비교", "가격 이력", "시술 사전"],
        horizontal=True, label_visibility="collapsed",
        key="evt_sub_view",
    )

    if sub_view == "이벤트 목록":
        _render_event_list()
    elif sub_view == "이벤트 검색":
        _render_event_search()
    elif sub_view == "지점 비교":
        _render_branch_compare()
    elif sub_view == "가격 이력":
        _render_price_history()
    elif sub_view == "시술 사전":
        _render_treatment_dictionary()


def _render_event_list():
    """현재 기간 이벤트 목록."""
    df = load_current_events()

    if len(df) == 0:
        st.warning("이벤트 데이터가 없습니다. 사이드바에서 '이벤트 동기화'를 실행해주세요.")
        return

    # 필터 영역
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        regions = sorted(df["지역"].unique())
        sel_region = st.selectbox("지역", ["전체"] + regions, key="evt_region")
    with col_f2:
        categories = sorted(df["카테고리"].unique())
        sel_cat = st.selectbox("카테고리", ["전체"] + categories, key="evt_cat")
    with col_f3:
        branches = sorted(df["지점명"].unique())
        sel_branch = st.selectbox("지점", ["전체"] + branches, key="evt_branch")

    # 필터 적용
    filtered = df.copy()
    if sel_region != "전체":
        filtered = filtered[filtered["지역"] == sel_region]
    if sel_cat != "전체":
        filtered = filtered[filtered["카테고리"] == sel_cat]
    if sel_branch != "전체":
        filtered = filtered[filtered["지점명"] == sel_branch]

    # 기간 + 건수 표시
    period = df["기간"].iloc[0] if len(df) > 0 else ""
    st.markdown(f"**이벤트 목록** · {period} · {len(filtered):,}건")

    # 데이터 표시
    display_df = filtered[["지점명", "지역", "카테고리", "이벤트명", "정상가", "이벤트가", "할인율", "비고"]].copy()
    display_df["정상가"] = display_df["정상가"].apply(_format_price)
    display_df["이벤트가"] = display_df["이벤트가"].apply(_format_price)
    display_df["할인율"] = display_df["할인율"].apply(
        lambda x: f"{x:.0f}%" if pd.notna(x) and x is not None else "-"
    )

    st.dataframe(
        display_df,
        use_container_width=True,
        height=600,
        hide_index=True,
        column_config={
            "지점명": st.column_config.TextColumn("지점", width="small"),
            "지역": st.column_config.TextColumn("지역", width="small"),
            "카테고리": st.column_config.TextColumn("카테고리", width="small"),
            "이벤트명": st.column_config.TextColumn("이벤트명", width="large"),
            "정상가": st.column_config.TextColumn("정상가", width="small"),
            "이벤트가": st.column_config.TextColumn("이벤트가", width="small"),
            "할인율": st.column_config.TextColumn("할인율", width="small"),
            "비고": st.column_config.TextColumn("비고", width="medium"),
        },
    )

    # CSV 다운로드
    csv = filtered[["지점명", "지역", "카테고리", "이벤트명", "정상가", "이벤트가", "할인율", "비고"]].to_csv(index=False).encode("utf-8-sig")
    st.download_button("CSV 다운로드", csv, f"events_{period}.csv", "text/csv", use_container_width=True)


def _render_event_search():
    """이벤트 통합 검색 — 이벤트명 + 패키지 내 시술명까지 분해 검색."""
    st.subheader("이벤트 검색")
    query = st.text_input(
        "이벤트명 또는 시술명 검색",
        placeholder="예: 울쎄라, 리쥬란, 보톡스, MLA",
        key="evt_search_q",
    )

    if not query:
        st.caption(
            "검색어를 입력하면 **이벤트명**뿐 아니라 **패키지 내 개별 시술명·브랜드**까지 탐색합니다."
        )
        # 등록된 시술 마스터 미리보기
        with st.expander("등록된 시술 목록 보기", expanded=False):
            treat_df = load_treatment_list()
            if len(treat_df) > 0:
                st.dataframe(
                    treat_df[["시술명", "브랜드", "카테고리", "사용횟수"]],
                    use_container_width=True, hide_index=True, height=300,
                )
            else:
                st.info("아직 등록된 시술이 없습니다. 이벤트 동기화를 먼저 실행해주세요.")
        return

    # 시술명 분해 검색 실행
    results = search_by_treatment(query)

    if len(results) == 0:
        st.info(f"'{query}'에 해당하는 이벤트가 없습니다.")
        return

    # 매칭 유형별 건수
    name_match = len(results[results["매칭유형"] == "이벤트명"])
    comp_match = len(results[results["매칭유형"] == "시술구성"])
    # 중복 제거된 고유 이벤트 수
    unique_events = results.drop_duplicates(subset=["id"])
    unique_count = len(unique_events)

    st.markdown(
        f"**검색 결과** · 총 **{unique_count:,}건** "
        f"(이벤트명 매칭 {name_match}건 · 시술구성 매칭 {comp_match}건)"
    )

    # 요약 통계
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("보유 지점 수", f"{unique_events['지점명'].nunique()}")
    with col2:
        st.metric("카테고리 수", f"{unique_events['카테고리'].nunique()}")
    with col3:
        prices = unique_events["이벤트가"].dropna()
        st.metric("최저 이벤트가", _format_price(prices.min()) if len(prices) > 0 else "-")
    with col4:
        st.metric("최고 이벤트가", _format_price(prices.max()) if len(prices) > 0 else "-")

    # 결과 테이블
    display = unique_events[["지점명", "지역", "카테고리", "이벤트명", "정상가", "이벤트가", "할인율", "패키지", "매칭유형", "비고"]].copy()
    display["정상가"] = display["정상가"].apply(_format_price)
    display["이벤트가"] = display["이벤트가"].apply(_format_price)
    display["할인율"] = display["할인율"].apply(
        lambda x: f"{x:.0f}%" if pd.notna(x) else "-"
    )
    display["패키지"] = display["패키지"].apply(lambda x: "✅" if x else "")

    st.dataframe(
        display,
        use_container_width=True, hide_index=True, height=500,
        column_config={
            "지점명": st.column_config.TextColumn("지점", width="small"),
            "지역": st.column_config.TextColumn("지역", width="small"),
            "카테고리": st.column_config.TextColumn("카테고리", width="small"),
            "이벤트명": st.column_config.TextColumn("이벤트명", width="large"),
            "정상가": st.column_config.TextColumn("정상가", width="small"),
            "이벤트가": st.column_config.TextColumn("이벤트가", width="small"),
            "할인율": st.column_config.TextColumn("할인율", width="small"),
            "패키지": st.column_config.TextColumn("PKG", width="small"),
            "매칭유형": st.column_config.TextColumn("매칭", width="small"),
            "비고": st.column_config.TextColumn("비고", width="medium"),
        },
    )

    # CSV 다운로드
    csv = unique_events[["지점명", "지역", "카테고리", "이벤트명", "정상가", "이벤트가", "할인율", "비고"]].to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        f"검색결과 CSV 다운로드 ({unique_count}건)", csv,
        f"search_{query}.csv", "text/csv", use_container_width=True,
    )


def _render_branch_compare():
    """지점별 이벤트 비교."""
    df = load_current_events()
    if len(df) == 0:
        st.warning("이벤트 데이터가 없습니다.")
        return

    all_branches = sorted(df["지점명"].unique())
    selected = st.multiselect(
        "비교할 지점 선택 (2개 이상)",
        options=all_branches,
        default=[],
        key="evt_compare_branches",
    )

    if len(selected) < 2:
        st.info("2개 이상의 지점을 선택해주세요.")
        return

    compare_df = df[df["지점명"].isin(selected)]

    # 카테고리별 이벤트 수 비교
    st.markdown("**카테고리별 이벤트 수 비교**")
    cat_count = compare_df.groupby(["지점명", "카테고리"]).size().reset_index(name="이벤트수")
    fig = px.bar(
        cat_count, x="카테고리", y="이벤트수", color="지점명",
        barmode="group",
        color_discrete_sequence=["#2563EB", "#059669", "#D97706", "#DC2626", "#7C3AED"],
    )
    fig.update_layout(
        height=400, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=12, color="#64748B"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig, use_container_width=True)

    # 지점별 평균 할인율 비교
    st.markdown("**지점별 평균 할인율 비교**")
    avg_discount = compare_df.groupby("지점명")["할인율"].mean().sort_values(ascending=False).reset_index()
    avg_discount["할인율"] = avg_discount["할인율"].round(1)
    st.dataframe(avg_discount, use_container_width=True, hide_index=True)


def _render_price_history():
    """가격 이력 조회."""
    evt_branches = load_evt_branches()
    branch_names = [b["name"] for b in evt_branches]

    sel_branch = st.selectbox("지점 선택", branch_names, key="evt_history_branch")
    search = st.text_input("이벤트명 검색 (선택)", key="evt_history_search")

    history_df = load_price_history(
        branch_name=sel_branch,
        event_name=search if search else None,
    )

    if len(history_df) == 0:
        st.info("해당 조건의 가격 이력이 없습니다.")
        return

    st.markdown(f"**가격 이력** · {sel_branch} · {len(history_df):,}건")

    display = history_df[["기간", "카테고리", "이벤트명", "정상가", "이벤트가", "할인율"]].copy()
    display["정상가"] = display["정상가"].apply(_format_price)
    display["이벤트가"] = display["이벤트가"].apply(_format_price)
    display["할인율"] = display["할인율"].apply(
        lambda x: f"{x:.0f}%" if pd.notna(x) else "-"
    )

    st.dataframe(display, use_container_width=True, hide_index=True, height=500)


# ============================================================
# 시술 사전 뷰
# ============================================================

def _render_treatment_dictionary():
    """시술 사전 — 시술/장비 설명 조회 + 관리자 편집."""
    permissions = get_permissions()
    can_edit = permissions.get("can_edit_dictionary", False)

    df = load_treatment_dictionary()
    if len(df) == 0:
        st.warning("시술 사전 데이터가 없습니다. init_db.py를 실행해주세요.")
        return

    # 통계
    total = len(df)
    verified = len(df[df["검수완료"] == 1])
    with_desc = len(df[df["설명"].notna() & (df["설명"] != "")])

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("전체 시술", f"{total}개")
    with col2:
        st.metric("설명 등록", f"{with_desc}개")
    with col3:
        st.metric("검수 완료", f"{verified}개", delta=f"{total - verified}개 미검수" if verified < total else None)

    # 필터
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        categories = sorted(df["카테고리"].dropna().unique())
        sel_cat = st.selectbox("카테고리", ["전체"] + categories, key="dict_cat")
    with col_f2:
        sel_status = st.selectbox("검수 상태", ["전체", "검수완료", "미검수"], key="dict_status")
    with col_f3:
        search = st.text_input("시술명 검색", key="dict_search")

    filtered = df.copy()
    if sel_cat != "전체":
        filtered = filtered[filtered["카테고리"] == sel_cat]
    if sel_status == "검수완료":
        filtered = filtered[filtered["검수완료"] == 1]
    elif sel_status == "미검수":
        filtered = filtered[filtered["검수완료"] == 0]
    if search:
        mask = (
            filtered["시술명"].str.contains(search, case=False, na=False)
            | filtered["브랜드"].str.contains(search, case=False, na=False)
        )
        filtered = filtered[mask]

    st.markdown(f"**시술 사전** · {len(filtered):,}건")

    # 테이블 표시
    display = filtered[["시술명", "브랜드", "카테고리", "설명", "검수완료", "이벤트사용수"]].copy()
    display["검수완료"] = display["검수완료"].apply(lambda x: "✅" if x == 1 else "⬜")

    st.dataframe(
        display,
        use_container_width=True, hide_index=True, height=450,
        column_config={
            "시술명": st.column_config.TextColumn("시술명", width="medium"),
            "브랜드": st.column_config.TextColumn("브랜드", width="small"),
            "카테고리": st.column_config.TextColumn("카테고리", width="small"),
            "설명": st.column_config.TextColumn("설명", width="large"),
            "검수완료": st.column_config.TextColumn("검수", width="small"),
            "이벤트사용수": st.column_config.NumberColumn("이벤트", width="small"),
        },
    )

    # ── 관리자 편집 영역 ──
    if not can_edit:
        st.caption("시술 설명 편집은 편집자/관리자 권한이 필요합니다.")
        return

    st.divider()
    st.subheader("시술 설명 편집")

    # 편집 대상 선택
    treatment_options = filtered[["id", "시술명", "브랜드"]].copy()
    treatment_options["label"] = treatment_options.apply(
        lambda r: f"{r['시술명']} ({r['브랜드']})" if pd.notna(r["브랜드"]) else r["시술명"],
        axis=1,
    )
    sel_idx = st.selectbox(
        "편집할 시술 선택",
        range(len(treatment_options)),
        format_func=lambda i: treatment_options.iloc[i]["label"],
        key="dict_edit_sel",
    )

    if sel_idx is not None:
        sel_row = filtered.iloc[sel_idx]
        with st.form("edit_treatment_form"):
            st.markdown(f"**{sel_row['시술명']}** · {sel_row['브랜드'] or '-'} · {sel_row['카테고리'] or '-'}")
            new_desc = st.text_area(
                "설명 (1~2줄 권장)",
                value=sel_row["설명"] if pd.notna(sel_row["설명"]) else "",
                height=100,
                key="dict_edit_desc",
            )
            new_verified = st.checkbox(
                "검수 완료",
                value=bool(sel_row["검수완료"] == "✅" if isinstance(sel_row["검수완료"], str) else sel_row["검수완료"]),
                key="dict_edit_verified",
            )
            submitted = st.form_submit_button("저장", type="primary", use_container_width=True)
            if submitted:
                ok = update_treatment_info(int(sel_row["id"]), new_desc, 1 if new_verified else 0)
                if ok:
                    st.success("저장 완료!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("저장 실패")

    # ── 새 시술 추가 ──
    with st.expander("새 시술 추가", expanded=False):
        with st.form("add_treatment_form"):
            at_name = st.text_input("시술명", key="dict_add_name")
            at_brand = st.text_input("브랜드 (선택)", key="dict_add_brand")
            cat_list = load_evt_categories()
            cat_options = {c["display_name"]: c["id"] for c in cat_list}
            at_cat = st.selectbox("카테고리", list(cat_options.keys()), key="dict_add_cat")
            at_desc = st.text_area("설명", key="dict_add_desc", height=80)
            add_submitted = st.form_submit_button("추가", use_container_width=True)
            if add_submitted:
                if not at_name:
                    st.error("시술명을 입력해주세요.")
                else:
                    ok = add_treatment_entry(at_name, at_brand, cat_options[at_cat], at_desc)
                    if ok:
                        st.success(f"'{at_name}' 추가 완료!")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("추가 실패 (중복 확인)")
