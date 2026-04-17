# [Archived] HANDOVER.md — Streamlit 관련 섹션

> **원본**: `docs/HANDOVER.md` (2026-03-20 기준)
> **이관일**: 2026-04-17
> **사유**: Streamlit은 2026-03-22 완전 폐기되고 FastAPI+Vue 단독 운영으로 전환. 원본에서 제거 후 이곳에 스냅샷으로 보관.

---

## 운영 구조 (병행 운영 시절)

```
사용자 → 포털 페이지 (portal/index.html)
           ├─ [Stream 버전] → Streamlit (:8501) — 레거시
           └─ [Fast 버전]   → Vue.js (:5173) → FastAPI (:8000)
```

- **DB 공유**: Streamlit과 FastAPI 양쪽에서 동일한 `data/equipment.db` 사용
- **비즈니스 로직 공유**: `cafe/db.py`, `equipment/db.py`, `events/db.py`를 양쪽에서 import
- **독립 인증**: Streamlit은 HMAC 토큰, FastAPI는 JWT(HS256)

## 기술 스택 (레거시 행)

| 계층 | 기술 | 비고 |
|------|------|------|
| 레거시 | Streamlit | 병행 운영 중, 추후 제거 예정 |

## 디렉토리 구조 (레거시 파일)

```
├── app.py, ui_tabs.py, auth.py    ← Streamlit 레거시 (수정 금지)
├── cafe/
│   └── ui.py                      # Streamlit UI (레거시)
```

## Docker Compose

```
docker-compose.yml                 ← 4 컨테이너 (portal, streamlit, api, frontend)
```

## 레거시 Streamlit 실행 방법

```bash
cd uni-portal
streamlit run app.py --server.port 8501
```

## 주의사항

- **Streamlit import**: `cafe/db.py` 등에서 `import streamlit as st`가 try/except로 감싸져 있음. FastAPI에서도 import 가능.
- **Streamlit 백업**: `_streamlit_backup/` 폴더에 기존 Streamlit 관련 파일이 보존됨. 복원 방법은 해당 폴더의 README.md 참고.
