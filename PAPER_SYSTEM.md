# 논문 분석 시스템 — 구현 현황 및 구조

> 최종 업데이트: 2026-03-22
> 목적: 다음 세션에서 이 문서를 참고하여 기존 구현을 이해하고 후속 작업을 이어갈 수 있도록 정리

---

## 1. 시스템 개요

미용의료 논문 PDF를 Claude API로 분석하여, **의학 비전문가 칼럼 작가**가 이해할 수 있는 서술형 요약을 생성하고 DB에 저장하는 시스템.

```
논문 PDF → [paper_analyzer.py] → Claude API 분석 → DB 저장 + Word/Excel 출력
                                                         ↓
                                              uni-portal 웹앱에서 조회
```

---

## 2. 구현 완료 항목

### 2.1 CLI 분석 도구 (`paper_analyzer.py`)

| 기능 | 설명 |
|------|------|
| PDF 텍스트 추출 | PyMuPDF (fitz) |
| DOI 추출 | 정규식 기반 |
| CrossRef 메타데이터 | DOI → 제목/저자/학술지/연도 자동 조회 |
| **학술 논문 검증** | 비학술 자료 (AI 정리, 개인 컴파일) 자동 필터링. 학술 마커 vs 비학술 패턴 점수 비교 |
| **중복 체크** | 3단계: 파일 해시(SHA-256) → DOI 일치 → 제목 매칭. API 호출 전 수행 |
| **Claude API 분석** | 서술형 줄 글 요약 (연구목적/설계/결과/결론/주의점) |
| 장비/시술 매칭 | DB의 device_info(127개) + evt_treatments(1699개)와 자동 매칭 |
| DB 저장 | papers 테이블에 직접 INSERT |
| Word 출력 | 시술별 섹션, 논문당 상세 보고서 |
| Excel 출력 | 시술별 시트, 논문당 1행 요약 |

#### 실행 방법
```bash
# 환경변수 필요
export ANTHROPIC_API_KEY="sk-ant-..."

# 분석 + DB 저장
python paper_analyzer.py --dir papers/

# 분석만 (DB 저장 안 함)
python paper_analyzer.py --dry-run paper.pdf

# 기존 JSON에서 문서만 재출력
python paper_analyzer.py --export-only paper_results/papers_YYYYMMDD.json
```

#### 분석 파이프라인 순서
```
PDF 텍스트 추출 → DOI 추출 → 학술 논문 검증 → 중복 체크 → CrossRef → Claude API → 장비 매칭 → DB 저장 + 문서 출력
                                ↑ 비학술이면 skip     ↑ 중복이면 skip
                                  (API 비용 0)          (API 비용 0)
```

### 2.2 DB 스키마 확장

`papers` 테이블에 추가된 컬럼:

| 컬럼 | 설명 |
|------|------|
| `one_line_summary` | 육하원칙 기반 한 줄 요약 (3~4문장) |
| `research_purpose` | 연구 목적 (서술형, 전문용어 풀이 포함) |
| `study_design_detail` | 연구 설계 및 방법 (서술형) |
| `key_results` | 핵심 결과 (서술형, 수치 포함) |
| `conclusion` | 연구 결론 (서술형) |
| `quotable_stats` | 인용 가능 수치 (JSON 배열) |
| `cautions` | 해석 시 주의점 (이해상충, 표본 한계 등) |
| `follow_up_period` | 추적 기간 |
| `file_hash` | 파일 SHA-256 해시 (중복 체크용) |

### 2.3 API 확장

- `api/models.py` — PaperCreate/PaperUpdate에 위 필드 모두 추가됨
- `api/routers/papers.py` — INSERT/SELECT 쿼리에 새 컬럼 반영됨
- 기존 8개 엔드포인트 모두 정상 작동

### 2.4 프론트엔드 (PapersView)

| 파일 | 역할 |
|------|------|
| `frontend/src/api/papers.ts` | API 클라이언트 (목록/상세/수정/삭제) |
| `frontend/src/stores/papers.ts` | Pinia 상태관리 (필터, 로딩) |
| `frontend/src/views/PapersView.vue` | 2컬럼 레이아웃 (좌: 논문 카드 목록, 우: 상세 패널) |
| `frontend/src/router/index.ts` | `/papers` 경로 추가됨 |
| `frontend/src/components/common/AppSidebar.vue` | "시술논문" 메뉴 추가됨 |

**PapersView 구조:**
- 좌측 (38%): 논문 카드 리스트 — 시술명 뱃지, 근거 수준 별표(★), 연구 유형, 상태 뱃지
- 우측: 상세 패널 — 한 줄 요약(파란 박스), 핵심 결과(초록 박스), 연구목적/설계/결과/결론(회색 박스), 주의점(주황 박스), 키워드
- 필터: 상태별(초안/검토됨/검증됨), 텍스트 검색

---

## 3. LLM 프롬프트 핵심 규칙

프롬프트는 `paper_analyzer.py`의 `ANALYSIS_PROMPT` 변수에 정의됨.

### 제목 번역 규칙
- 고정 구조: **[시술명] + [기술 설명] + [적응증/효과] + [문헌 형식]**
- 원문 의미 최대한 보존, 과도한 함축 금지
- 어색한 학술 번역어만 교체: "회춘"→"노화 개선", "비침습적"→"비수술적"
- 예: "울쎄라에 적용되는 시각화 마이크로 집속 초음파(MFU-V)의 안면 노화 개선 효과: 종합 리뷰"

### 한 줄 요약 규칙
- 육하원칙: 누가/무엇을/어떻게/왜/결과
- 3~4문장, 이 요약만 읽으면 논문 핵심 파악 가능

### 서술 원칙
- 서술형 줄 글 (글머리 기호 나열 X)
- 전문 용어 첫 등장 시 괄호 안 쉬운 설명
- 복잡한 개념은 "※ 쉽게 말하면:" 보충
- 이해상충(스폰서/제조사) 반드시 cautions에 명시

---

## 4. 미구현 / 후속 작업

### 4.1 대량 처리
- 논문 PDF 폴더: `Z:\스마트브랜딩 팀 공유 폴더\블로그 폴더\유앤아이의원\0. 논문 관련\`
- 총 394건 PDF (주요 폴더 129건)
- 폴더별 순차 처리 권장 (00_리프팅 → 01_필러 → ...)

### 4.2 논문-블로그 연동 (웹앱 기능)
- 특정 논문으로 작성된 블로그 원고가 이미 있는지 체크하는 기능
- papers 테이블에 `linked_articles` 또는 별도 연결 테이블 필요
- PapersView에서 "이 논문으로 발행된 원고" 섹션 추가

### 4.3 웹앱 PDF 업로드
- 프론트엔드에서 PDF 업로드 → 서버에서 분석 → 결과 표시
- API Key 입력 필드 (개인 키로 분석)
- 진행 상태 실시간 표시

### 4.4 EquipmentView 연동 — **구현 완료** (2026-03-22)
- `EquipmentView.vue`의 "관련 논문" 섹션 활성화됨
- 장비 클릭 시 `GET /papers/by-device/{device_info_id}`로 관련 논문 자동 로드
- 논문 카드에 근거 수준 별표, 연구 유형, 한 줄 요약 표시
- 카드 클릭 → `/papers?id=N`으로 PapersView 상세 이동

---

## 5. 파일 목록

### 신규 생성
```
paper_analyzer.py              — CLI 분석 도구 (메인)
frontend/src/api/papers.ts     — API 클라이언트
frontend/src/stores/papers.ts  — Pinia 상태관리
paper_results/                 — 분석 결과 출력 디렉토리 (JSON/DOCX/XLSX)
```

### 수정됨
```
requirements.txt               — anthropic, pymupdf, python-docx 추가
init_db.py                     — papers 테이블 9개 컬럼 추가
api/models.py                  — PaperCreate/PaperUpdate 확장
api/routers/papers.py          — INSERT/SELECT 새 컬럼 반영
frontend/src/views/PapersView.vue      — placeholder → 2컬럼 UI
frontend/src/views/EquipmentView.vue   — 관련 논문 섹션 활성화 (2026-03-22)
frontend/src/router/index.ts           — /papers 경로 추가
frontend/src/components/common/AppSidebar.vue — 시술논문 메뉴 추가
```

---

## 6. 의존성

```
anthropic     — Claude API 클라이언트
pymupdf       — PDF 텍스트 추출 (import fitz)
python-docx   — Word 문서 출력
openpyxl      — Excel 출력 (기존 의존성)
```

## 7. 현재 DB 상태

papers 테이블에 3건 등록됨:
- #2: 써마지 4세대 델파이 합의 (써마지, 근거1)
- #3: 치과 초음파 영상 종합 리뷰 (미분류, 근거4)
- #4: 7MHz HIFU 조직 응고 기전 (미분류, 근거1)
