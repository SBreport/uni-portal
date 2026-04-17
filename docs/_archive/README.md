# 문서 아카이브

> 이 폴더는 **더 이상 현재 프로젝트 상태를 반영하지 않는** 문서들을 보관합니다.
> 즉시 삭제하지 않는 이유: 과거 맥락 확인이나 복원이 필요할 수 있어서.

## 보관 정책

- **즉시 삭제 X, 이관 후 관찰** — 1~2개월 간 문제없으면 완전 삭제 가능
- 모든 파일은 **Git에 기록**되므로 삭제 후에도 `git log`로 복원 가능
- 아래 표에 이관 사유를 반드시 명시

## 폴더 구조

| 폴더 | 용도 |
|------|------|
| `completed/` | 이미 완료된 기획안 (구현 완료, 더 이상 액션 불필요) |
| `legacy/` | 폐기된 기술 스택·기능 설명 (참고용 스냅샷) |
| `stale/` | 현재 상태를 반영하지 못하는 구 문서 (STRUCTURE.md, DEPLOY.md로 대체됨) |

---

## 이관 이력

| 이관일 | 파일 | 원래 위치 | 사유 |
|--------|------|----------|------|
| 2026-04-17 | `completed/PLAN-001_DB분리.md` | `docs/plans/` | 4-DB 분리 구현 + NAS 배포 완료. 기획안으로서의 역할 종료. |
| 2026-04-17 | `legacy/HANDOVER_streamlit_sections.md` | `docs/HANDOVER.md` 내 Streamlit 관련 섹션 | Streamlit은 2026-03-22 완전 폐기, FastAPI 단독 운영. 혼동 방지 위해 분리. |
| 2026-04-17 | `stale/HANDOVER.md` | `docs/HANDOVER.md` | 블로그/플레이스/웹페이지를 "placeholder"로 기술하지만 실제로는 모두 구현 완료. 현재 상태는 `STRUCTURE.md` + `DEPLOY.md`가 대체. |
| 2026-04-17 | `stale/PROJECT_ROADMAP.md` | 루트 | v1.9 기준이나 실제는 v2.0+. 현재 상태 기록은 `STRUCTURE.md`가 대체. 미래 로드맵은 별도 세션에서 재작성 예정. |

---

## 복원 방법

필요 시 파일을 원래 위치로 되돌리면 됩니다:
```bash
mv docs/_archive/completed/PLAN-001_DB분리.md docs/plans/
```

또는 Git 히스토리로 내용 확인:
```bash
git log --all --full-history -- docs/plans/PLAN-001_DB분리.md
```
