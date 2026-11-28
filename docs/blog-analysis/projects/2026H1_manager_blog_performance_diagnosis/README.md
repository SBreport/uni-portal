# 2026H1 담당자 기준 블로그 성과 진단

2026년 1월~6월 블로그 데이터를 사수/부사수/최적블로그 전문 담당자 기준으로 진단하기 위한 프로젝트다.

## 목적

- 지점 단위가 아니라 담당 역할 단위로 블로그 노출 성과를 확인한다.
- 어떤 사수/부사수/최적블로그 전문 담당자 기준에서 노출율이 높은지, 낮은지 진단한다.
- 성과 분석 전에 DB의 담당자 컬럼이 분석축으로 사용 가능한지 먼저 감사한다.

## 현재 단계

1차 단계는 `담당자 컬럼 감사표` 작성이다.

- 기준표: `manager_reference_mapping.csv`
- 부사수 기준표: `sub_manager_reference_mapping.csv`
- 생성 스크립트: `generate_author_audit.mjs`
- 감사 CSV: `manager_author_column_audit.csv`
- 부사수 6월 배정 확인 CSV: `sub_manager_author_audit.csv`
- 부사수 6월 요약 CSV: `sub_manager_summary.csv`
- 사수 월별 요약 CSV: `manager_monthly_summary.csv`
- 사수 담당 지점 최적블로그 월별 요약 CSV: `manager_optimal_branch_monthly_summary.csv`
- 부사수 월별 요약 CSV: `sub_manager_monthly_summary.csv`
- 최적전문 월별 요약 CSV: `optimal_specialist_monthly_summary.csv`
- 미매칭 감사 CSV: `manager_unmatched_branch_audit.csv`
- author_main 내부 검증 CSV: `author_main_summary.csv`
- 감사 HTML: `manager_author_column_audit.html`

## 기준 기간

- 2026-01-01 ~ 2026-06-30

## 주의

현재 제공된 사수표는 2026년 6월 기준이다. 1~5월 담당 구조와 다를 수 있으므로, 성과 분석 단계에서는 이 기준 차이를 별도 메모해야 한다.

부사수표도 2026년 6월 기준이다. DB에는 별도 부사수 컬럼이 충분히 채워져 있지 않으므로, 부사수 월별 표는 기준표의 `부사수`와 DB `author_main`을 대조해 집계한다.

서동균, 박주혁은 최적블로그 전문 발행 담당자로 분리한다. 사수/부사수 기준 성과를 볼 때 이들의 작성분은 별도 탭에서 확인한다.

사수 월별 성과는 담당 지점 기준으로 집계하며, 일반 블로그와 최적 블로그를 분리해 표시한다. 사수 담당 지점 최적블로그 성과는 작성자가 누구인지와 관계없이, 해당 사수가 맡은 지점에서 발행된 최적블로그만 모아 집계한다.

`author_main_summary.csv`는 사수+부사수+최적전문을 한 화면에서 보는 보고용 표가 아니라, DB 작성자 컬럼을 검증하기 위한 내부 산출물이다.
