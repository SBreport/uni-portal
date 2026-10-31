# 2026H1 최적블로그 유앤/로컬 실패율 진단

2026년 1~6월 최적블로그 원고의 실패율을 유앤/로컬, 계정, 지점 단위로 진단한 프로젝트다.

## 주요 산출물

- `optimal_blog_2026H1_report.html`: 최종 웹 리포트
- `optimal_blog_analysis_plan.md`: 프로젝트 기획서
- `optimal_blog_target_audit.md`: 분석 대상 감사 문서
- `db_source.md`: 분석 기준 DB와 갱신 절차
- `optimal_blog_2026H1_detail.csv`: 상세 원고 데이터
- `optimal_blog_2026H1_monthly_by_group.csv`: 월별 그룹 집계
- `optimal_blog_2026H1_monthly_by_blog.csv`: 월별 계정 집계

## 현재 기준

- 분석 기간: 2026-01-01 ~ 2026-06-30
- 분석 대상: 최적블로그 계열 원고
- 제외: 준최/NB 68건
- 보정 포함: 홍보성글로 잘못 분류된 최적 원고 1건
- 실패: 순위 0, 빈값, 11위 이상
- 핵심 지표: 발행건, 실패수, 실패율, 미노출, 상위10밖

공통 기준은 `../../standards/블로그분석_공통기준.md`를 따른다.

DB 관리 기준은 `../../standards/블로그분석_DB관리기준.md`를 따른다.
