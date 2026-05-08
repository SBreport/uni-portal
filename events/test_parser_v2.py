"""parser.py v2 케이스 검증 테스트.

실행: python -m events.test_parser_v2
"""

from events.parser import (
    find_category_marker,
    is_header_row,
    parse_branch_sheet,
    validate_parsed_events,
)


def _pass(label: str) -> None:
    print(f"  PASS  {label}")


def _fail(label: str, detail: str) -> None:
    print(f"  FAIL  {label} — {detail}")


# ── 케이스 1: # 서브카테고리 마커 인식 ─────────────────────────────────────

def test_case1_hash_marker():
    label = "케이스1 # 서브카테고리 마커"

    # 인식해야 하는 케이스 — 한글
    assert find_category_marker("#레이저 리프팅") == "레이저 리프팅", "한글 바로"
    result_slash = find_category_marker("#보톡스/윤곽")
    assert result_slash is not None, "한글 시작 + 슬래시 조합 인식 실패"
    assert find_category_marker("#보톡스·윤곽") == "보톡스·윤곽", "한글 시작"
    assert find_category_marker("# 리프팅") == "리프팅", "공백 후 한글"
    # 인식해야 하는 케이스 — 영문/숫자 시작 (결함 1 수정 후)
    assert find_category_marker("#ECM 스킨부스터") == "ECM 스킨부스터", "영문 시작 + 한글 조합"
    assert find_category_marker("#DCA") == "DCA", "영문 약어 3자"
    assert find_category_marker("#FCR 필링") == "FCR 필링", "영문 + 공백 + 한글"
    assert find_category_marker("#LDM") == "LDM", "영문 약어 3자"
    assert find_category_marker("#V쎄라 윤곽PKG") == "V쎄라 윤곽PKG", "영문+한글 혼합"
    assert find_category_marker("#3D 입술필러") == "3D 입술필러", "숫자 시작"
    # 제외해야 하는 케이스 — 단순 # 또는 # 뒤 공백만
    assert find_category_marker("#") is None, "# 단독"
    assert find_category_marker("# ") is None, "# + 공백만"
    # ■ 기존 동작 유지
    assert find_category_marker("■ 단독이벤트") == "단독이벤트", "■ 기존 동작"

    _pass(label)


# ── 케이스 2: 이벤트명 컬럼 다중 매칭 (광교 케이스) ─────────────────────────

def test_case2_duplicate_name_col():
    label = "케이스2 이벤트명 컬럼 중복 (광교)"

    # 헤더 행: col1=이벤트명, col2=이벤트명, col3=정상가, col4=이벤트가, col5=비고
    # 데이터: col1 비어있고 col2에 실제 이름
    rows = [
        ["■ 단독이벤트"],
        ["이벤트명", "이벤트명", "정상가", "이벤트가", "비고"],
        ["", "울쎄라 600샷", "800000", "390000", ""],
        ["", "써마지 FLX", "900000", "450000", ""],
    ]
    events = parse_branch_sheet(rows, "광교")
    if not events:
        _fail(label, "이벤트가 비어있음")
        return
    if events[0].display_name != "울쎄라 600샷":
        _fail(label, f"첫 이벤트명 오류: {events[0].display_name!r}")
        return
    _pass(label)


# ── 케이스 3: 비고 컬럼 이후 추가 셀 합산 (부산 F열 케이스) ──────────────────

def test_case3_notes_merge():
    label = "케이스3 비고 이후 추가 셀 합산"

    rows = [
        ["■ 이달의 단독이벤트"],
        ["이벤트명", "정상가", "이벤트가", "비고", ""],
        ["카카오톡 인증", "150000", "79000", "카카오톡 풀친 대상", "4/22 추가"],
    ]
    events = parse_branch_sheet(rows, "부산")
    if not events:
        _fail(label, "이벤트가 비어있음")
        return
    notes = events[0].notes
    if "카카오톡 풀친 대상" not in notes or "4/22 추가" not in notes:
        _fail(label, f"notes 합산 안됨: {notes!r}")
        return
    if " / " not in notes:
        _fail(label, f"구분자 없음: {notes!r}")
        return
    _pass(label)


# ── 케이스 4: 멀티라인 헤더 셀 처리 (선릉 케이스) ─────────────────────────────

def test_case4_multiline_header():
    label = "케이스4 멀티라인 헤더 셀 (선릉)"

    rows = [
        ["■ 5-6월 단독이벤트"],
        ["이벤트명", "정상가", "최종 이벤트가", "특이사항\n★용량 중복적용 안됨. 추가 용량 시 정상가 안내 ★"],
        ["울쎄라 300샷", "500000", "250000", "토요일 불가"],
    ]
    # is_header_row가 멀티라인 셀을 올바르게 처리하는지 확인
    header_row = rows[1]
    if not is_header_row(header_row):
        _fail(label, "멀티라인 헤더 행 인식 실패")
        return
    events = parse_branch_sheet(rows, "선릉")
    if not events:
        _fail(label, "이벤트가 비어있음")
        return
    if events[0].notes != "토요일 불가":
        _fail(label, f"비고 파싱 오류: {events[0].notes!r}")
        return
    _pass(label)


# ── 케이스 5: NOTES_KEYWORDS 확장 (특이사항, 관리 순서) ──────────────────────

def test_case5_notes_keywords():
    label = "케이스5 NOTES_KEYWORDS 확장"

    # 특이사항 컬럼
    rows_a = [
        ["■ 이달의 이벤트"],
        ["이벤트명", "정상가", "이벤트가", "특이사항"],
        ["리쥬비엘 1cc", "200000", "99000", "초진만 가능"],
    ]
    events_a = parse_branch_sheet(rows_a, "선릉")
    if not events_a:
        _fail(label + " (특이사항)", "이벤트가 비어있음")
        return
    if events_a[0].notes != "초진만 가능":
        _fail(label + " (특이사항)", f"notes 오류: {events_a[0].notes!r}")
        return

    # 관리 순서 컬럼 (여의도)
    rows_b = [
        ["■ 첫방문 이벤트"],
        ["카테고리", "이벤트명", "정상가", "이벤트가", "관리 순서"],
        ["리프팅", "울쎄라 600샷", "800000", "390000", "1. 세안 2. 시술"],
    ]
    events_b = parse_branch_sheet(rows_b, "여의도")
    if not events_b:
        _fail(label + " (관리 순서)", "이벤트가 비어있음")
        return
    if events_b[0].notes != "1. 세안 2. 시술":
        _fail(label + " (관리 순서)", f"notes 오류: {events_b[0].notes!r}")
        return

    _pass(label)


# ── 케이스 6: 정상가 컬럼 인식 안정성 (광명/부평/천호) ─────────────────────

def test_case6_regular_price_variants():
    label = "케이스6 정상가 컬럼 변형 인식"

    variants = [
        ("광명", ["이벤트명", "정상가(이벤트가*49%)", "이벤트가", "비고"]),
        ("부평", ["이벤트명", "부평점 정상가(*49%)", "부평점 이벤트가", "비고"]),
        ("천호", ["이벤트명", "정상가(*1.8)", "확정 이벤트가", "비고"]),
    ]
    for branch, header in variants:
        rows = [
            ["■ 단독이벤트"],
            header,
            ["울쎄라 600샷", "800000", "390000", ""],
        ]
        events = parse_branch_sheet(rows, branch)
        if not events:
            _fail(label + f" ({branch})", "이벤트가 비어있음")
            return
        if events[0].regular_price != 800000:
            _fail(label + f" ({branch})", f"정상가 오류: {events[0].regular_price}")
            return
        if events[0].event_price != 390000:
            _fail(label + f" ({branch})", f"이벤트가 오류: {events[0].event_price}")
            return
    _pass(label)


# ── 케이스 7: 가격 없는 단일 텍스트 행 → 카테고리 안전망 ─────────────────────

def test_case7_implicit_category():
    label = "케이스7 가격 없는 단일 텍스트 행 → 카테고리 안전망"

    rows = [
        ["■ 첫방문 이벤트"],
        ["이벤트명", "정상가", "이벤트가", "비고"],
        ["리프팅", "", "", ""],         # 카테고리 행 (# 마커 없이)
        ["울쎄라 600샷", "800000", "390000", ""],
        ["보톡스·윤곽", "", "", ""],     # 두 번째 카테고리 행
        ["보톡스 100u", "300000", "150000", ""],
    ]
    events = parse_branch_sheet(rows, "테스트")
    names = [e.display_name for e in events]
    cats = [e.raw_category for e in events]

    # "리프팅", "보톡스·윤곽"은 이벤트로 저장되면 안 됨
    if "리프팅" in names:
        _fail(label, "'리프팅'이 이벤트로 저장됨")
        return
    if "보톡스·윤곽" in names:
        _fail(label, "'보톡스·윤곽'이 이벤트로 저장됨")
        return

    # 울쎄라는 카테고리="리프팅"이어야 함
    idx_ul = names.index("울쎄라 600샷") if "울쎄라 600샷" in names else -1
    if idx_ul == -1:
        _fail(label, "울쎄라 600샷 누락")
        return
    if cats[idx_ul] != "리프팅":
        _fail(label, f"울쎄라 카테고리 오류: {cats[idx_ul]!r}")
        return

    # 보톡스는 카테고리="보톡스·윤곽"이어야 함
    idx_bt = names.index("보톡스 100u") if "보톡스 100u" in names else -1
    if idx_bt == -1:
        _fail(label, "보톡스 100u 누락")
        return
    if cats[idx_bt] != "보톡스·윤곽":
        _fail(label, f"보톡스 카테고리 오류: {cats[idx_bt]!r}")
        return

    _pass(label)


# ── 케이스 8: validate_parsed_events 가격 없음 issue ──────────────────────

def test_case8_validate_no_price():
    label = "케이스8 validate 가격 없음 issue"

    rows = [
        ["■ 단독이벤트"],
        ["이벤트명", "정상가", "이벤트가", "비고"],
        ["이름만 있는 행", "", "", ""],
    ]
    events = parse_branch_sheet(rows, "테스트")
    # 가격 없는 이름만 있는 행은 케이스7 안전망으로 카테고리 처리되므로 events 비어있어야 함
    # 만약 이벤트로 들어갔다면 validate가 issue로 잡아야 함
    # 두 케이스 모두 테스트
    from events.parser import ParsedEvent
    dummy = ParsedEvent(
        raw_event_name="가격없는항목",
        raw_category="테스트",
        display_name="가격없는항목",
        regular_price=None,
        event_price=None,
        discount_rate=None,
        notes="",
        session_count=None,
        is_package=False,
        row_order=1,
        components=["가격없는항목"],
    )
    issues = validate_parsed_events([dummy])
    found = any("가격 정보 없음" in i["issue"] for i in issues)
    if not found:
        _fail(label, f"가격 없음 issue 미등록: {issues}")
        return
    _pass(label)


# ── 케이스 9: 데이터 비고 셀 내 개행 플래트닝 (선릉 윤곽톡스 케이스) ───────────

def test_case9_notes_multiline_flatten():
    label = "케이스9 비고 셀 내 개행 플래트닝 (선릉 윤곽톡스)"

    # col4(특이사항) 셀에 개행이 있는 실제 데이터 패턴
    rows = [
        ["■ 첫방문"],
        ["이벤트명", "정상가", "최종 이벤트가", "특이사항\n★용량 중복적용 안됨. 추가 용량 시 정상가 안내 ★"],
        [
            "첫방문고객) 윤곽톡스 (국산)",
            "14000",
            "9000",
            "* 4-6주안에 내원시리터치비용 : 22,000원\n턱밑 or 귀밑 침샘 중복 적용 가능",
        ],
    ]
    events = parse_branch_sheet(rows, "선릉")
    if not events:
        _fail(label, "이벤트가 비어있음")
        return

    # notes에 \n이 없어야 하고, 두 줄이 ' / '로 합쳐져야 함
    notes = events[0].notes
    if "\n" in notes:
        _fail(label, f"notes에 개행 잔류: {notes!r}")
        return
    if "4-6주" not in notes:
        _fail(label, f"첫 줄 내용 누락: {notes!r}")
        return
    if "턱밑 or 귀밑" not in notes:
        _fail(label, f"두 번째 줄 내용 누락: {notes!r}")
        return
    if " / " not in notes:
        _fail(label, f"줄 간 구분자 없음: {notes!r}")
        return

    # 헤더 멀티라인 셀의 ★ 텍스트가 데이터 notes에 들어오지 않아야 함
    if "★" in notes:
        _fail(label, f"헤더 부가 텍스트(★)가 notes에 포함됨: {notes!r}")
        return

    _pass(label)


# ── 케이스 10: 비고 셀에 "이벤트" 단어 포함된 헤더 (여의도 케이스) ───────────

def test_case10_long_notes_cell_in_header():
    label = "케이스10 비고 셀에 '이벤트' 포함된 헤더 (여의도)"

    # 여의도 시트 라인 637 헤더 재현:
    #   col 4 = "최종 제안가" (가격 헤더)
    #   col 5 = "10회 결제 고객 대상 이벤트: 지인 소개 시 진정관리 1회 서비스 (홈페이지 노출 X)"
    #     ← 비고 안내문이지만 "이벤트" 단어 포함
    # 기존 룰에선 col 5를 col_event로 잘못 잡아서 데이터 행의 비고 셀을 가격으로 파싱.
    rows = [
        ["■ 남성 제모(젠틀맥스 프로플러스)"],
        ["", "카테고리", "이벤트명", "", "최종 제안가",
         "10회 결제 고객 대상 이벤트: 지인 소개 시 진정관리 1회 서비스 (홈페이지 노출 X)"],
        ["", "남성 패키지", "男) 인기 패키지 1회", "", "43,000", ""],
        ["", "", "男) 인기 패키지 10회", "", "250,000",
         "10회 결제 고객 대상 이벤트: 지인 소개 시 진정관리 1회 서비스 (홈페이지 노출 X)"],
    ]
    events = parse_branch_sheet(rows, "여의도")

    if len(events) != 2:
        _fail(label, f"이벤트 2건 기대, 실제 {len(events)}")
        return

    # "최종 제안가" 컬럼이 event_price로 매핑돼야 함
    e1 = next((e for e in events if "1회" in e.display_name), None)
    if e1 is None:
        _fail(label, "1회 항목 누락")
        return
    if e1.event_price != 43000:
        _fail(label, f"1회 이벤트가 오류: {e1.event_price} (43000 기대)")
        return

    # 10회: 비고 셀에 "10회 결제..." 텍스트 있어도 event_price에 영향 없어야 함
    e2 = next((e for e in events if "10회" in e.display_name), None)
    if e2 is None:
        _fail(label, "10회 항목 누락")
        return
    if e2.event_price != 250000:
        _fail(label, f"10회 이벤트가 오류: {e2.event_price} (250000 기대, 비고 '10' 잘못 파싱하면 10원)")
        return

    # validator도 실패 안 해야 함 (가격 정상 인식됐으니)
    issues = validate_parsed_events(events)
    if any("가격 정보 없음" in i["issue"] for i in issues):
        _fail(label, f"'가격 정보 없음' 거짓 양성: {issues}")
        return

    _pass(label)


def main():
    print("=" * 50)
    print("parser.py v2 케이스 검증")
    print("=" * 50)
    tests = [
        test_case1_hash_marker,
        test_case2_duplicate_name_col,
        test_case3_notes_merge,
        test_case4_multiline_header,
        test_case5_notes_keywords,
        test_case6_regular_price_variants,
        test_case7_implicit_category,
        test_case8_validate_no_price,
        test_case9_notes_multiline_flatten,
        test_case10_long_notes_cell_in_header,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__} - AssertionError: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR {t.__name__} - {type(e).__name__}: {e}")
            failed += 1
    print("-" * 50)
    print(f"결과: {passed} passed / {failed} failed")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
