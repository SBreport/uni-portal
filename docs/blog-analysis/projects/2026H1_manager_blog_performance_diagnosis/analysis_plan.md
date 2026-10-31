# 담당자 기준 블로그 성과 진단 기획

## 1. 분석 배경

기존 블로그 분석은 지점 단위로 노출율을 진단했다. 이번 프로젝트는 같은 데이터를 담당 역할 기준으로 묶어, 사수/부사수/최적블로그 전문 담당자별 성과 차이를 확인하기 위한 분석이다.

## 2. 1차 목표

성과 분석 전에 담당자 컬럼을 감사한다.

- DB의 `author_main`이 실제 작성자 성격으로 사용 가능한지 확인
- DB의 `author_sub`가 사수 분석에 사용할 수 있는 수준인지 확인
- 6월 기준 부사수표와 DB `author_main`이 얼마나 일치하는지 확인
- 6월 기준 사수표와 DB 지점명이 얼마나 매칭되는지 확인
- 매칭되지 않는 지점명과 사수표에 있으나 발행이 없는 지점을 분리
- 서동균, 박주혁은 최적블로그 전문 발행 담당자로 분리
- 사수/부사수/최적전문 모두 월 단위 발행건, 노출건, 노출율과 1~6월 종합 성과를 확인
- 사수가 담당하는 지점군의 최적블로그 발행 성과는 작성자와 관계없이 별도 집계

## 3. 기준 데이터

- DB: `data/equipment.db`
- 테이블: `blog_posts`
- 기간: 2026년 1월~6월
- 사수 기준표: `manager_reference_mapping.csv`
- 부사수 기준표: `sub_manager_reference_mapping.csv`

## 4. 1차 산출물

- `manager_author_column_audit.csv`
- `manager_unmatched_branch_audit.csv`
- `author_main_summary.csv`
- `manager_author_column_audit.html`
- `sub_manager_author_audit.csv`
- `sub_manager_summary.csv`
- `manager_monthly_summary.csv`
- `manager_optimal_branch_monthly_summary.csv`
- `sub_manager_monthly_summary.csv`
- `optimal_specialist_monthly_summary.csv`

## 5. 다음 단계

감사표 확인 후 다음을 결정한다.

- 사수 성과는 사수 기준표의 담당 지점군으로 집계하되, 부사수명/최적전문명으로 확인되는 작성분은 별도 집계한다
- 사수 담당 지점 최적블로그 성과는 작성자가 누구인지와 관계없이, 해당 사수 담당 지점의 최적블로그 발행분만 모아 집계한다
- 부사수 원고 퀄리티는 6월 기준 `sub_manager_reference_mapping.csv`와 DB `author_main` 대조 결과를 기준으로 월별/종합 집계한다
- 최적블로그 전문 담당자 작성분은 사수/부사수 성과와 분리해 별도 확인한다
- 1~5월 담당 변경 이력을 별도 보정할지
- 기준표 미매칭 데이터는 작성자 기준으로 `최적전문 가능`, `부사수 가능`, `사수/담당자 가능`, `기준표 외 데이터`로 1차 분류한다
- 담당자별 HTML 리포트에 포함할 탭 구성

권장 보고서 탭:

- 요약
- 사수 월별
- 사수 담당 최적블
- 부사수 월별
- 최적전문
- 미매칭 분류
