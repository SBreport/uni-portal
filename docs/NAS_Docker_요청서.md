# NAS Docker 환경 구성 요청서

> **요청일**: 2026-03-12
> **요청자**: 스마트브랜딩
> **프로젝트명**: uni-portal (유앤아이의원 통합 관리 시스템)

---

## 1. 요청 개요

<!-- 이 시스템이 무엇인지 설명합니다 -->

유앤아이의원 전 지점(44개+)의 **장비, 이벤트, 카페마케팅** 데이터를
하나의 웹 앱에서 통합 관리하는 시스템입니다.

- **하나의 URL, 하나의 DB, 하나의 컨테이너**로 운영됩니다
- 웹 브라우저로 접속하며, 별도 프로그램 설치가 필요 없습니다
- Docker 컨테이너로 실행되므로 NAS 시스템에 영향을 주지 않습니다

---

## 2. NAS에 필요한 사항

<!-- NAS 담당자가 준비해야 할 항목들입니다 -->

### 2-1. Docker 환경

| 항목 | 요구 사항 | 설명 |
|------|----------|------|
| Docker | 설치 필요 | NAS 패키지 센터에서 "Docker" 또는 "Container Manager" 설치 |
| docker-compose | 설치 필요 | Docker와 함께 보통 자동 설치됨 |
| 포트 | **8501번** 1개 | 웹 브라우저 접속용 포트 (다른 서비스와 겹치지 않는지 확인) |

> **참고**: **8501번 포트**가 이미 사용 중이면, 다른 포트를 배정하고 알려주세요.

### 2-2. NAS 폴더 구조

<!-- 아래 경로에 폴더를 만들어주세요. 파일은 저희가 전달합니다. -->

```
/volume1/docker/uni-portal/          ← 앱 전체 파일이 들어가는 폴더
├── data/                            ← DB 파일이 저장되는 폴더 (자동 생성됨)
│   ├── equipment.db                 ← SQLite 데이터베이스 (장비+이벤트 통합, 자동 생성)
│   └── backups/                     ← 매일 자동 백업 (7일 보관, 자동 생성됨)
├── normalization/                   ← 이벤트 카테고리 매핑 설정 파일
│   ├── category_map.json            ← 비표준 카테고리 → 표준 매핑
│   └── treatment_patterns.json      ← 시술 브랜드/용량 패턴
├── equipment/                       ← 장비 관리 모듈 (패키지)
│   ├── __init__.py
│   ├── db.py                        ← 장비 DB 읽기/쓰기
│   └── sync.py                      ← 장비 Google Sheets 동기화
├── events/                          ← 이벤트 관리 모듈 (패키지)
│   ├── __init__.py
│   ├── db.py                        ← 이벤트 DB 읽기/쓰기
│   ├── sync.py                      ← 이벤트 수집 파이프라인
│   ├── parser.py                    ← 시트 파서
│   ├── normalizer.py                ← 카테고리/시술 정규화
│   ├── price_parser.py              ← 가격 파싱
│   ├── validators.py                ← 데이터 검증
│   └── ui.py                        ← 이벤트 탭 UI
├── .streamlit/                      ← Streamlit 설정 폴더
│   ├── config.toml                  ← 앱 테마/서버 설정
│   └── secrets.toml                 ← 인증 설정 (비밀번호 해시값)
├── credentials.json                 ← Google Sheets API 인증 (이벤트 수집용, 별도 제공)
├── app.py                           ← 메인 앱 파일
├── auth.py                          ← 로그인/인증 모듈
├── users.py                         ← 사용자 관리 모듈
├── config.py                        ← 설정 파일
├── ui_tabs.py                       ← 화면 탭 라우팅 + 장비 UI
├── init_db.py                       ← DB 초기화 스크립트 (장비+이벤트 테이블)
├── requirements.txt                 ← Python 패키지 목록
├── Dockerfile                       ← Docker 이미지 빌드 설정
├── docker-compose.yml               ← Docker 실행 설정
└── entrypoint.sh                    ← 컨테이너 시작 스크립트
```

### 2-3. 별도 제공 파일: credentials.json

<!-- 이벤트 데이터 수집에 필요한 인증 파일입니다 -->

이벤트 데이터는 Google Sheets에서 가져옵니다.
이를 위해 **Google 서비스 계정 인증 파일** (`credentials.json`)이 필요합니다.

- 이 파일은 **저희가 별도로 전달**합니다
- `/volume1/docker/uni-portal/credentials.json` 경로에 업로드해주세요
- 이벤트 동기화 기능을 사용하지 않으면 없어도 앱 자체는 정상 동작합니다

### 2-4. 시스템 사양

<!-- 이 앱이 NAS에서 사용하는 리소스 양입니다 -->

| 항목 | 사양 | 설명 |
|------|-----|------|
| 메모리 | 최대 512MB | docker-compose.yml에서 제한 설정 완료 |
| 디스크 | 약 500MB | Docker 이미지 + DB + 백업 포함 |
| CPU | 제한 없음 | 일반적인 NAS에서 충분히 동작 |
| 네트워크 | 내부망 | 외부 공개 불필요 (사내 접속만) |

---

## 3. 설치 및 실행 방법

<!-- NAS 담당자가 순서대로 따라하면 됩니다 -->

### 3-1. 파일 업로드

1. NAS에 `/volume1/docker/uni-portal/` 폴더를 생성합니다
2. 전달받은 `uni-portal/` 폴더의 **모든 파일**을 위 경로에 업로드합니다
3. 전달받은 `credentials.json` 파일을 같은 경로에 업로드합니다

> **주의**: `normalization/` 폴더와 `.streamlit/` 폴더도 함께 업로드해야 합니다.
> 폴더 구조가 그대로 유지되도록 업로드해주세요.

### 3-2. 환경 변수 설정 (선택)

<!-- 이벤트 동기화 기능을 사용할 경우에만 필요합니다 -->

이벤트 동기화를 위해 Google Sheets ID가 필요합니다.
`docker-compose.yml` 파일에 이미 설정되어 있으며, 변경이 필요하면 아래 값을 수정합니다:

```yaml
environment:
  - EVENT_SHEET_ID=여기에_구글시트_ID_입력    # 이벤트 데이터가 있는 Google Sheets ID
```

> **참고**: 시트 ID는 저희가 별도로 안내합니다. 기본값이 설정되어 있으므로
> 특별한 안내가 없으면 수정하지 않아도 됩니다.

### 3-3. Docker 이미지 빌드 및 실행

NAS에 SSH로 접속하거나 Docker UI에서 아래 명령어를 실행합니다:

```bash
# 1. 프로젝트 폴더로 이동
cd /volume1/docker/uni-portal

# 2. Docker 이미지 빌드 + 컨테이너 시작 (최초 1회)
docker-compose up -d --build

# 3. 정상 실행 확인
docker ps | grep uni-portal
```

<!-- 빌드가 완료되면 컨테이너가 자동으로 시작됩니다 -->

### 3-4. 접속 확인

- 브라우저에서 `http://[NAS_IP]:8501` 로 접속합니다
- 로그인 화면이 나오면 정상입니다
- 초기 관리자 계정: **ID** `admin` / **비밀번호** `admin1234`
- **최초 로그인 후 반드시 비밀번호를 변경해주세요**

---

## 4. 운영 관련

<!-- 설치 이후 운영에 필요한 정보입니다 -->

### 4-1. 자동으로 처리되는 것들

<!-- 앱이 알아서 처리하므로 NAS 담당자가 할 일이 없습니다 -->

| 작업 | 주기 | 설명 |
|------|-----|------|
| 장비 데이터 동기화 | 매일 새벽 3시 | Google Sheets → DB, 새 데이터만 추가 |
| 이벤트 데이터 동기화 | 매월 1일, 15일 새벽 4시 | Google Sheets → DB, 격월 이벤트 수집 |
| DB 백업 | 동기화 시 자동 | 7일간 보관 후 자동 삭제 |
| 컨테이너 자동 재시작 | NAS 재부팅 시 | `restart: always` 설정 완료 |

### 4-2. 수동 관리가 필요한 것들

<!-- 웹 앱에서 관리자가 직접 해야 하는 작업들입니다 -->

| 작업 | 방법 | 빈도 |
|------|-----|------|
| 사용자 계정 추가 | 웹 앱 → 사용자 관리 탭 | 필요 시 |
| 장비 수동 동기화 | 웹 앱 → 사이드바 "장비 동기화" 버튼 | 필요 시 |
| 이벤트 수동 동기화 | 웹 앱 → 사이드바 "이벤트 동기화" 버튼 (admin 전용) | 필요 시 |
| 앱 업데이트 | 파일 교체 후 `docker-compose up -d --build` | 업데이트 시 |

### 4-3. 문제 발생 시 확인 방법

```bash
# 컨테이너 상태 확인
docker ps -a | grep uni-portal

# 컨테이너 로그 확인 (최근 50줄)
docker logs --tail 50 uni-portal

# 컨테이너 재시작
docker restart uni-portal

# 컨테이너 중지 후 재빌드 (업데이트 시)
docker-compose down
docker-compose up -d --build
```

---

## 5. docker-compose.yml 내용

<!-- 실제 사용되는 설정 파일입니다. 참고용으로 첨부합니다. -->

```yaml
version: "3.8"

services:
  uni-portal:                        # 서비스 이름 (통합 포털)
    build: .                         # 현재 폴더의 Dockerfile로 빌드
    container_name: uni-portal       # 컨테이너 이름
    ports:
      - "8501:8501"                  # 호스트:컨테이너 포트 매핑
    volumes:
      - ./data:/app/data             # DB 파일을 NAS에 영구 저장
      # Google Sheets API 인증 파일 (이벤트 동기화용)
      - ./credentials.json:/app/credentials.json:ro
    restart: always                  # NAS 재부팅 시 자동 재시작
    mem_limit: 512m                  # 메모리 사용량 제한
    environment:
      - TZ=Asia/Seoul                # 한국 시간대 설정
      # 이벤트 시트 ID (Google Sheets)
      - EVENT_SHEET_ID=${EVENT_SHEET_ID:-}
      - GOOGLE_CREDENTIALS_FILE=/app/credentials.json
```

### 주요 설정 설명

| 설정 | 값 | 의미 |
|------|---|------|
| `build: .` | 현재 폴더 | Dockerfile을 이용해 이미지를 직접 빌드합니다 |
| `ports: "8501:8501"` | 포트 매핑 | NAS의 8501 포트로 접속하면 컨테이너의 8501 포트로 연결됩니다 |
| `volumes: ./data:/app/data` | 데이터 영구 저장 | 컨테이너를 삭제해도 DB 데이터는 NAS에 남아있습니다 |
| `volumes: ./credentials.json` | 인증 파일 | Google Sheets 접근용 인증 파일을 읽기 전용으로 마운트합니다 |
| `restart: always` | 자동 재시작 | NAS가 재부팅되면 컨테이너도 자동으로 다시 시작됩니다 |
| `mem_limit: 512m` | 메모리 제한 | 앱이 512MB 이상 메모리를 사용하지 않도록 제한합니다 |
| `TZ=Asia/Seoul` | 시간대 | 로그와 동기화 시간을 한국 시간 기준으로 설정합니다 |
| `EVENT_SHEET_ID` | 시트 ID | 이벤트 데이터를 가져올 Google Sheets의 고유 ID입니다 |
| `GOOGLE_CREDENTIALS_FILE` | 인증 경로 | 컨테이너 내부에서 인증 파일의 경로를 지정합니다 |

---

## 6. 확인 요청 사항

<!-- NAS 담당자에게 확인받아야 할 항목들입니다 -->

- [ ] Docker (또는 Container Manager)가 설치되어 있나요?
- [ ] 8501번 포트가 다른 서비스에서 사용 중이지 않나요?
- [ ] `/volume1/docker/` 경로에 폴더 생성이 가능한가요?
- [ ] SSH 접속이 가능한가요? (또는 Docker UI에서 빌드 가능한가요?)
- [ ] NAS의 여유 메모리가 512MB 이상 있나요?
- [ ] NAS에서 외부 인터넷 접속이 가능한가요? (Docker 이미지 빌드 시 필요)

---

## 7. 요청자 정보

| 항목 | 내용 |
|------|------|
| 요청자 | 스마트브랜딩 |
| 프로젝트 | uni-portal (통합 관리 시스템) |
| 연락처 | (담당자 연락처 기입) |
| 비고 | 포트 1개(8501), 컨테이너 1개만 사용하는 경량 앱입니다 |
