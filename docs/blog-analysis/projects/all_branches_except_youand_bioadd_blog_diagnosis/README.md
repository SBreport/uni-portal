# 전체 지점 블로그 노출율 진단

유앤아이 계열과 bioadd lab 7개 지점을 제외한 운영 지점의 일반 블로그/최적 블로그 노출율을 진단하는 프로젝트다.

## 분석 범위

- 기간: 2026-01-01 ~ 2026-06-30
- 포함: `blog_channel`이 `br`, `opt`인 블로그 발행 데이터
- 제외: 유앤아이 계열 지점, bioadd lab 7개 지점
- 메인 진단: 2026년 6월 운영 지점 기준표와 매칭된 지점
- 기준 DB: `data/equipment.db`

## 현재 데이터

- 원본 추출 데이터: 2,337건
- 기준표 매칭 분석대상: 2,245건
- 기준표 매칭 지점: 31개
- 일반 블로그: 1,050건, 노출율 74.0%
- 최적 블로그: 1,195건, 노출율 76.1%
- 전체 노출율: 75.1%
- 기준표 외 데이터: 92건

## 지점/과목 기준

- 기준표: `branch_reference_mapping.csv`
- 지점명은 `project_branch`, `branch_name`, `target_branch` 순서로 확인한 뒤 원고번호와 배포표기를 제거한다.
- 과목명과 로컬/솔루션 구분은 기준표 매칭값을 우선한다.
- 기준표에 없는 데이터는 메인 진단에서 제외하고 `unmatched_reference_audit.csv`로 분리한다.

## 파일

- `(2026.06)all_branches_report.html`: 웹페이지 리포트
- `(2026.06)all_branches_june_report.html`: 2026년 6월 현황 보고용 웹페이지 리포트
- `generate_june_report.mjs`: 6월 현황 보고서 재생성 스크립트
- `june_branch_summary.csv`: 6월 지점별 요약 데이터
- `june_detail.csv`: 6월 상세 데이터
- `analysis_plan.md`: 프로젝트 목적과 분석 기준
- `target_audit.md`: 데이터 포함/제외 감사
- `db_source.md`: DB 기준과 갱신 가이드
- `branch_reference_mapping.csv`: 운영 지점/과목 기준표
- `normalized_branch_summary.csv`: 기준표 매칭 지점별 요약
- `normalized_account_summary.csv`: 기준표 매칭 지점 x 계정 ID 요약
- `normalized_detail.csv`: 분석 대상 지점/과목 포함 상세 데이터
- `unmatched_reference_audit.csv`: 기준표 외 데이터
- `reference_gap_diagnosis.md`: 기준표 외 데이터 진단 메모
- `target_count_audit.md`: 후보 지점 수와 실제 분석 대상 지점 수 차이 진단
- `target_detail.csv`: 분석 대상 상세 데이터
- `target_summary.csv`: 지점별/유형별 요약
- `monthly_summary.csv`: 월별 요약
- `generate_report.mjs`: 리포트/정규화 CSV 재생성 스크립트
