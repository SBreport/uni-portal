# 블로그 분석

유니포털 블로그 데이터 분석 산출물을 보관하는 정식 문서 공간이다.

## 폴더 구조

- `standards/`: 분석마다 공통으로 적용할 정의, 포함/제외 기준, 지표 기준
- `db-snapshots/`: 운영 웹에서 내려받은 블로그 분석용 DB 보관본
- `projects/`: 기간, 목적, 분석 대상이 다른 개별 분석 프로젝트

## 현재 프로젝트

- `projects/2026H1_optimal_blog_youand_local/`
  - 2026년 1~6월 최적블로그 실패율 진단
  - 유앤/로컬 그룹, 계정, 지점 기준 분석
  - 준최/NB 제외, 홍보성글 오분류 1건 보정 포함

- `projects/bioadd_lab_analysis_report/`
  - bioadd lab 타겟 7개 지점 블로그 성과 진단
  - 브블/일반과 최블 구분 비교
  - 1차 데이터 확보 및 기준 정리 진행 중

- `projects/all_branches_except_youand_bioadd_blog_diagnosis/`
  - 2026년 1~6월 전체 지점 블로그 성과 진단
  - 유앤아이 계열과 bioadd lab 7개 지점 제외
  - 일반 블로그와 최적 블로그를 함께 진단

- `projects/2026H1_manager_blog_performance_diagnosis/`
  - 2026년 1~6월 담당자/사수 기준 블로그 성과 진단
  - 6월 기준 지점별 사수표와 DB 담당자 컬럼 감사
  - 성과 분석 전 `author_main`, `author_sub` 사용 가능성 확인

## 공통 기준 문서

- `standards/블로그분석_공통기준.md`
- `standards/블로그분석_DB관리기준.md`
- `standards/블로그분석_보고서생성가이드.md`

## DB 보관 원칙

운영 웹에서 내려받은 블로그 DB는 `db-snapshots/`에 보관한다. 분석 프로젝트는 해당 스냅샷을 로컬 `data/equipment.db`에 반영한 뒤 진행하며, 프로젝트별 `db_source.md`에 사용한 DB 파일명, 해시, row 수, 최신 발행일을 기록한다.

## 기본 원칙

블로그 분석은 단순 발행량 확인이 아니라 운영 의사결정을 위한 진단 도구다.

- 분석 대상 정의를 먼저 확정한다.
- 성공/실패 기준을 문서화한다.
- 데이터 오류와 운영상 예외를 분리한다.
- 계정 문제, 지점 문제, 키워드 문제를 섞어 판단하지 않는다.
- 임시 분석이 끝나면 반드시 `projects/` 하위 폴더로 승격한다.

## 반복 운영 방식

앞으로 블로그 분석 요청은 다음 입력을 기준으로 새 프로젝트를 만든다.

- 분석 기간: 예) `2026년 1월~6월`
- 분석 대상: 예) 특정 지점 목록, 전체 지점, 유앤 제외, bioadd lab 제외
- 분석 유형: 예) 일반 블로그, 최적 블로그, 일반+최적 종합
- 제외 기준: 예) 유앤아이 계열 제외, 특정 프로젝트 지점 제외, 기준표 외 데이터 제외
- 보고서 관점: 예) 지점별 노출율, 월별 변화, 과목별 비교, 계정별 진단

새 프로젝트는 `projects/{프로젝트명}/` 하위에 만들고, 최종 산출물은 최소한 다음을 포함한다.

- `README.md`: 프로젝트 목적과 산출물 요약
- `analysis_plan.md`: 분석 목적, 기간, 포함/제외 기준
- `db_source.md`: 사용 DB 스냅샷과 로컬 반영 기준
- `target_detail.csv`: 분석 대상 상세 데이터
- `target_summary.csv` 또는 `normalized_branch_summary.csv`: 요약 데이터
- `generate_report.mjs`: 재생성 가능한 HTML 리포트 생성 스크립트
- `{보고서명}.html`: 최종 웹페이지 보고서
