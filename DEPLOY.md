> 현재 구현된 실제 상태를 기록한 문서입니다.

# 배포 흐름

## 전체 흐름 (한눈에)

```
[로컬 개발]
    → git push
    → [GitHub]
    → Portainer UI에서 수동 Pull & Redeploy
    → [Synology NAS Docker 컨테이너]
    → [웹앱 서비스]
```

---

## NAS의 역할

Synology NAS는 회사 내부에서 24시간 켜두는 자체 서버다. AWS 같은 클라우드 대신 NAS를 서버로 활용한다.  
NAS 위에 Docker가 설치되어 있고, **Portainer**는 Docker 컨테이너를 웹 UI로 관리하는 도구다.  
사용자는 NAS의 Docker 컨테이너에서 실행 중인 웹앱에 브라우저로 접속한다.

---

## 운영 URL

| 용도 | 주소 |
|------|------|
| 웹앱 | http://smartbranding.synology.me:8080/ |
| Portainer | `smartbranding.synology.me:<PORTAINER_PORT>` <!-- TODO: 실제 포트 기입 필요 --> |

도메인: Synology DDNS (`*.synology.me` 무료 제공)

---

## 로컬 개발 실행

```bash
# 백엔드 (FastAPI)
cd uni-portal
pip install -r api/requirements.txt
uvicorn api.main:app --reload --port 8000

# 프론트엔드 (별도 터미널)
cd frontend
npm install
npm run dev   # http://localhost:5173
```

Vite 프록시가 `/api/*` 요청을 `localhost:8000`으로 전달한다. 별도 CORS 설정 불필요.

---

## Docker 구성

두 컨테이너로 분리 운영.

| 컨테이너 | 이미지 | 포트 | 메모리 | 역할 |
|----------|--------|------|--------|------|
| `api` | FastAPI | 8000 | 256MB | REST API 서버 |
| `frontend` | Vue 빌드 + Nginx | 8080 | 64MB | 정적 파일 서빙 |

관련 파일: `Dockerfile.api`, `Dockerfile.frontend`, `docker-compose.yml`  
볼륨 `portal-data`에 SQLite DB 파일 4개와 `credentials.json`이 저장된다.

---

## 환경변수

`.env` 또는 Portainer 스택 환경변수 탭에 설정한다.

| 변수 | 용도 |
|------|------|
| `AUTH_SALT` | 비밀번호 해시 salt |
| `AUTH_BOOTSTRAP_ADMIN_ID` | 최초 관리자 계정 ID |
| `AUTH_BOOTSTRAP_ADMIN_PW_HASH` | 최초 관리자 비밀번호 해시 |
| `AUTH_BOOTSTRAP_ADMIN_ROLE` | 최초 관리자 역할 |
| `ALLOWED_ORIGINS` | CORS 허용 도메인 |
| `EVENT_SHEET_ID` | 이벤트 Google Sheets ID |
| `CAFE_SHEET_ID` | 카페 Google Sheets ID |
| `GOOGLE_CREDENTIALS_FILE` | 서비스 계정 키 경로 (`/app/data/credentials.json`) |

---

## 배포 절차 (Portainer 수동 Pull & Redeploy)

1. 로컬에서 코드 수정 후 커밋·푸시
   ```bash
   git commit -m "변경 내용"
   git push
   ```
2. 브라우저로 Portainer 접속
3. 좌측 **Stacks** 메뉴 → `uni-portal` 스택 선택
4. 상단 **Pull and redeploy** 버튼 클릭
5. Portainer가 자동으로 처리:
   - GitHub에서 최신 코드 pull
   - Docker 이미지 재빌드
   - 기존 컨테이너 중지 → 새 컨테이너 시작
6. 1~3분 후 http://smartbranding.synology.me:8080/ 에서 새 버전 확인
7. 로그 확인: Portainer → Containers → 해당 컨테이너 → **Logs**

---

## DB 백업·복원

- DB 파일 위치 (NAS): `/volume1/docker/uni-portal/data/` (Docker 볼륨 마운트 경로)
- **백업**: NAS 자체 스냅샷 기능 또는 해당 폴더를 수동 복사
- **복원**: 같은 경로에 파일 덮어쓰기 후 컨테이너 재시작

---

## 롤백

1. Portainer → Stacks → `uni-portal` → **Editor** 탭에서 이미지 태그 지정
2. 또는 `git revert` 후 재배포

---

> 최종 갱신일: 2026-04-17
