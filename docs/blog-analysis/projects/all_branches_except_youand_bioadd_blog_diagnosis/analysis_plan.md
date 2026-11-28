# 전체 지점 블로그 노출율 진단 - 분석 기획

## 목적

유앤아이 계열과 bioadd lab 7개 지점을 제외한 운영 지점의 블로그 노출 상황을 진단한다. 핵심 지표는 발행량이 아니라 일반 블로그 노출율과 최적 블로그 노출율이다.

이 보고서는 지점별로 다음 질문에 답하기 위한 자료다.

- 일반 블로그가 상위 10위 안에 안정적으로 노출되고 있는가?
- 최적 블로그가 상위 10위 안에 안정적으로 노출되고 있는가?
- 과목별 또는 지점별로 노출율 저하가 두드러지는 곳이 있는가?
- 일반 블로그 계정 ID와 지점 매칭이 정상적으로 보이는가?

## 분석 기간

- 2026년 1월 1일 ~ 2026년 6월 30일
- 기준 컬럼: `published_at`

## 포함 기준

- `blog_channel = br`: 일반 블로그
- `blog_channel = opt`: 최적 블로그
- 순위 기준:
  - 노출: `exposure_rank` 1~10
  - 미노출: `exposure_rank` 빈값 또는 0
  - 10위밖: `exposure_rank` 11 이상

## 운영 지점 기준표

이번 프로젝트는 2026년 6월 운영 지점 현황표를 기준으로 과목과 지점명을 매칭한다.

- 기준표 파일: `branch_reference_mapping.csv`
- 매칭 대상만 메인 진단에 포함한다.
- 기준표 외 데이터는 `unmatched_reference_audit.csv`로 분리한다.
- 유앤아이 계열과 bioadd lab 7개 지점은 기준표에 있어도 이번 프로젝트의 분석 대상에서 제외한다.

## 제외 기준

### 유앤아이 계열

다음 필드 중 하나라도 유앤아이 계열로 판단되면 제외한다.

- 분석 대상 지점명 `target_branch`
- `branch_name`
- `project_branch`
- `content_number`
- `keyword`

제외 키워드:

- `유앤%`
- `유앤아이%`
- keyword 내 `%유앤%`

### bioadd lab 7개 지점

다음 접두어가 `target_branch`, `branch_name`, `content_number`에 포함되면 제외한다.

- 글로우치과
- 날개병원
- 노블와이
- 아도의원
- 온우의원
- 청담미닛
- 청담위아르

## 분석 대상 지점명 기준

지점명은 다음 우선순위로 생성한 뒤 정규화한다.

1. `branch_name`
2. `project_branch`
3. `(blank)`

현재 리포트 생성 스크립트에서는 `project_branch`, `branch_name`, `target_branch` 순서로 더 명확한 지점명을 우선 사용한다. 이후 다음 요소를 제거하거나 통합한다.

- 원고번호: `굿플중랑 1`, `에이플 최적배포 12`의 숫자는 지점명이 아니라 월별 원고 번호다.
- 배포표기: `최적배포`, `준최배포`, `브블`, `NB`
- 축약명: `굿플중랑` -> `닥터굿플란트치과 중랑`, `맑은양평` -> `맑은미소치과 양평`

`준최배포` 명칭이 들어간 데이터가 `opt` 채널에 포함되어 있다. 이번 단계에서는 DB 채널 기준으로 최적 블로그에 포함하되, 최종 해석 시 별도 확인이 필요하다.

## 산출물

- 상세 데이터: `target_detail.csv`
- 기준표: `branch_reference_mapping.csv`
- 기준표 매칭 상세 데이터: `normalized_detail.csv`
- 기준표 매칭 지점별 요약: `normalized_branch_summary.csv`
- 기준표 매칭 지점 x 계정 ID 요약: `normalized_account_summary.csv`
- 기준표 외 데이터 감사: `unmatched_reference_audit.csv`
- 웹 리포트: `(2026.06)all_branches_report.html`
