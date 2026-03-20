# Streamlit 버전 백업

> 백업일: 2026-03-20
> 목적: FastAPI+Vue 단일 버전으로 전환하기 전 Streamlit 관련 파일 보존

## 포함 파일

| 파일 | 역할 |
|------|------|
| `app.py` | Streamlit 메인 엔트리포인트 |
| `ui_tabs.py` | 탭별 UI 렌더링 (장비/이벤트/카페/블로그/대시보드/관리자) |
| `auth.py` | Streamlit 세션 기반 인증 |
| `users.py` | 사용자 관리 (Streamlit optional import) |
| `cafe/ui.py` | 카페 Streamlit UI |
| `cafe/db.py` | 카페 DB (st.cache_data 포함 원본) |
| `events/ui.py` | 이벤트 Streamlit UI |
| `equipment/db.py` | 장비 DB (st.cache_data 포함 원본) |
| `Dockerfile` | Streamlit 컨테이너 빌드 |
| `entrypoint.sh` | Streamlit 실행 스크립트 |
| `requirements.txt` | Streamlit 포함 의존성 |
| `.streamlit/` | Streamlit 설정 (테마, 인증) |

## 복원 방법

이 폴더의 파일들을 프로젝트 루트에 복사하면 Streamlit 버전을 다시 실행할 수 있습니다.

```bash
# Streamlit 실행
pip install -r _streamlit_backup/requirements.txt
streamlit run _streamlit_backup/app.py --server.port=8501
```
