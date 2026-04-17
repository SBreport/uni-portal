# PLAN-001: DB 분리 (equipment / cafe / blog / system)

> 상태: 완료 (로컬 검증 완료, NAS 배포 필요)
> 작성일: 2026-03-22
> 예상 소요: 2~3세션
> 참조: ARCHITECTURE.md §3

---

## 목적

현재 모든 데이터가 `equipment.db` 한 파일에 혼재되어 있어서:
- 장비 DB 업로드 시 카페 원고 손실 위험
- 채널별 독립 관리 불가
- 백업/복원 시 전체를 다뤄야 함

**4개 DB로 분리하여 Fact(사실)과 Content(콘텐츠)를 독립 관리.**

---

## 현재 상태

```
data/
└── equipment.db (단일 파일, 25개 테이블)
    ├── device_info, papers, equipment, branches, categories  ← Fact
    ├── evt_*                                                  ← Fact
    ├── cafe_*                                                 ← Content
    └── users                                                  ← System
```

## 목표

```
data/
├── equipment.db    Fact (장비·논문·이벤트)     — 관리자 관리
├── cafe.db         카페 콘텐츠                 — 편집자 관리
├── blog.db         블로그 콘텐츠 (신규)        — 편집자 관리
└── system.db       사용자·설정                 — 시스템 관리
```

---

## 작업 단계

### Phase 1: system.db 분리 (가장 안전, 먼저 실행)

- [ ] `system.db` 생성 스크립트 작성
- [ ] `users` 테이블을 `system.db`로 이전
- [ ] `api/routers/auth.py` — DB 경로 변경
- [ ] `api/routers/users.py` — DB 경로 변경
- [ ] `users.py` — DB 경로 변경
- [ ] 로그인 테스트

### Phase 2: cafe.db 분리

- [ ] `cafe.db` 생성 스크립트 작성
- [ ] cafe_* 7개 테이블을 `cafe.db`로 이전:
  - cafe_periods
  - cafe_branch_periods
  - cafe_articles
  - cafe_comments
  - cafe_feedbacks
  - cafe_status_log
  - cafe_sync_log
- [ ] `cafe/db.py` — DB 경로를 `cafe.db`로 변경
- [ ] `api/routers/cafe.py` — 영향 확인
- [ ] cafe_articles에 `device_info_id` 컬럼 추가 (equipment.db 참조)
- [ ] 카페 동기화 테스트
- [ ] 원고 목록/편집 테스트

### Phase 3: blog.db 생성 (신규)

- [ ] `blog.db` 생성 스크립트 작성
- [ ] blog_articles, blog_tags, blog_status_log 테이블 생성
- [ ] `api/routers/blog.py` 라우터 생성
- [ ] 프론트엔드 BlogView 기본 구현

### Phase 4: equipment.db 정리

- [ ] equipment.db에서 cafe_*, users 테이블 제거
- [ ] `init_db.py` 4개 DB 대응으로 수정
- [ ] DB 업로드 API — equipment.db 전용으로 확인
- [ ] Docker Volume 테스트 (4파일 모두 같은 /app/data/)

---

## 영향 범위

| 파일 | 변경 내용 |
|------|----------|
| `cafe/db.py` | DB_PATH → `cafe.db` |
| `users.py` | DB_PATH → `system.db` |
| `api/routers/auth.py` | users import 경로 확인 |
| `api/routers/cafe.py` | cafe/db.py 의존, 변경 없을 수 있음 |
| `api/routers/equipment.py` | DB 업로드 — equipment.db만 처리 확인 |
| `init_db.py` | 4개 DB 초기화로 확장 |
| `equipment/matcher.py` | DB_PATH 확인 (equipment.db 유지) |
| `docker-compose.yml` | 볼륨 변경 없음 (같은 /app/data/) |

---

## 검증 방법

1. **로그인 정상** — system.db 분리 확인
2. **카페 원고 목록/편집 정상** — cafe.db 분리 확인
3. **장비 DB 업로드 시 카페 원고 유지** — 독립성 확인
4. **카페 동기화 시 장비 데이터 유지** — 독립성 확인
5. **보유장비 → 장비 클릭 → 시술+이벤트+카페 모두 표시** — 크로스 참조 확인
6. **Docker 배포 후 4개 DB 모두 정상** — 운영 확인

---

## 주의사항

- `device_info.id`는 절대 변경 금지 (cafe/blog에서 참조)
- SQLite는 cross-DB FK 미지원 → API 레이어에서 검증
- 마이그레이션 시 기존 데이터 백업 필수
- NAS 배포 시 Pull & Redeploy 후 DB 업로드 순서 확인
