# 논문 분석 프로그램 개발 가이드

> 목적: 미용의료 논문 PDF를 분석·요약하여 유앤아이의원 통합 관리 시스템(uni-portal)의 papers DB에 저장
> 최종 업데이트: 2026-03-22

---

## 1. 전체 흐름

```
논문 PDF 파일
    │
    ▼
[논문 분석 프로그램] ─── 이 가이드의 대상
    │
    │  1) PDF 텍스트 추출
    │  2) LLM으로 구조화된 정보 추출
    │  3) 시술/장비 매칭 (device_info, evt_treatments)
    │  4) JSON 생성
    │
    ▼
POST /papers/bulk  ─── uni-portal API
    │
    ▼
SQLite papers 테이블 저장
    │
    ▼
uni-portal 웹에서 조회 (보유장비 → 관련 논문)
```

---

## 2. 대상 DB: papers 테이블

### 2.1 스키마

| 필드 | 타입 | 필수 | 설명 | 예시 |
|------|------|------|------|------|
| `device_info_id` | INT | △ | 장비/시술 사전 FK (127개 중 매칭) | `1` (울쎄라피 프라임) |
| `treatment_id` | INT | △ | 시술 마스터 FK (1699개 중 매칭) | `15` (울쎄라) |
| `doi` | TEXT | △ | Digital Object Identifier | `10.1016/j.jaad.2024.01.023` |
| `title` | TEXT | **필수** | 원문 제목 (영문) | `Efficacy of HIFU for Facial Lifting` |
| `title_ko` | TEXT | 권장 | 한국어 번역 제목 | `안면 리프팅을 위한 HIFU의 효능` |
| `authors` | TEXT | 권장 | 저자 (첫 저자 et al.) | `Kim JH et al.` |
| `journal` | TEXT | 권장 | 학술지명 | `J Am Acad Dermatol` |
| `pub_year` | INT | 권장 | 출판 연도 | `2024` |
| `pub_date` | TEXT | △ | 출판일 | `2024-03-15` |
| `abstract_summary` | TEXT | **핵심** | 논문 요약 (한국어, 200~500자) | 아래 참조 |
| `key_findings` | TEXT | **핵심** | 핵심 발견 (한국어, bullet points) | 아래 참조 |
| `keywords` | TEXT | 권장 | JSON 배열 | `["HIFU","리프팅","울쎄라"]` |
| `evidence_level` | INT | 권장 | 근거 수준 (0~5) | `4` |
| `study_type` | TEXT | 권장 | 연구 유형 | `RCT` |
| `sample_size` | TEXT | △ | 표본 크기 | `120명` |
| `source_url` | TEXT | △ | PubMed/DOI 링크 | `https://pubmed.ncbi.nlm.nih.gov/12345` |
| `source_file` | TEXT | △ | 로컬 PDF 경로 | `papers/hifu_2024.pdf` |
| `status` | TEXT | 기본값 | 상태 | `draft` → `reviewed` → `verified` |

### 2.2 근거 수준 (evidence_level) 정의

| 레벨 | 연구 유형 | 설명 |
|------|----------|------|
| **5** | 메타분석 / 체계적 문헌고찰 | 여러 RCT를 종합 분석 |
| **4** | RCT (무작위 대조 시험) | 가장 신뢰도 높은 단일 연구 |
| **3** | 코호트 연구 / 비교 연구 | 대조군이 있는 관찰 연구 |
| **2** | 증례 보고 / 증례 시리즈 | 소규모 임상 경험 보고 |
| **1** | 전문가 의견 / 리뷰 | 체계적이지 않은 리뷰 |
| **0** | 미분류 | 분류 불가 |

### 2.3 연구 유형 (study_type) 값

```
메타분석, 체계적문헌고찰, RCT, 비무작위대조시험,
전향적코호트, 후향적코호트, 환자대조연구,
증례시리즈, 증례보고, 전문가리뷰, 내러티브리뷰
```

---

## 3. 연동 대상: 기존 시술/장비 데이터

### 3.1 device_info (장비/시술 사전) — 127개

논문이 다루는 **장비 또는 시술**과 매칭합니다.

| id | name | category |
|----|------|----------|
| 1 | 울쎄라피 프라임 | 리프팅 |
| 2 | 써마지FLX | 리프팅 |
| 3 | 써마지 | 리프팅 |
| 4 | 슈링크 유니버스 | 리프팅 |
| 5 | 인모드 | 리프팅 |
| 7 | 클라리티2 | 레이저(색소/혈관/제모) |
| 9 | 보톡스 | 주사 시술 |
| 10 | 리쥬란 | 스킨부스터 |
| 11 | 쥬베룩 | 스킨부스터 |
| 15 | 필러 | 주사 시술 |
| 19 | 포텐자 | RF 마이크로니들 |
| 21 | 피코슈어 | 레이저(색소) |
| 40 | CO2 레이저 | 레이저(점/사마귀) |
| 52 | 엑소좀 | 스킨부스터 |

> 전체 127개 목록: `GET /equipment/device-info` 또는 DB 직접 조회

### 3.2 evt_treatments (시술 마스터) — 1699개

이벤트에서 사용되는 **구체적 시술/브랜드** 사전입니다.

| id | name | brand | category |
|----|------|-------|----------|
| 1 | 보톡스 | 앨러간 | 보톡스 |
| 9 | 쥬비덤 | 앨러간 | 필러 |
| 15 | 울쎄라 | 멀츠 | 레이저리프팅 |
| 16 | 슈링크 | 클래시스 | 레이저리프팅 |
| 17 | 써마지 | 솔타메디컬 | 레이저리프팅 |
| 30 | 리쥬란 | 파마리서치 | 스킨부스터 |
| 31 | 쥬벨룩 | 에이비오 | 스킨부스터 |

> 전체 목록: `GET /events/treatments`

### 3.3 카테고리 (evt_categories) — 16개

| id | name | display_name |
|----|------|-------------|
| 2 | 레이저리프팅 | 레이저리프팅 |
| 3 | 실리프팅 | 실리프팅 |
| 4 | 보톡스 | 보톡스 |
| 5 | 필러 | 필러 |
| 6 | 색소 | 색소/기미/잡티 |
| 7 | 스킨케어 | 스킨케어 |
| 8 | 스킨부스터 | 스킨부스터 |
| 9 | 여드름 | 여드름/모공 |
| 10 | 제모 | 제모 |
| 11 | 비만 | 비만/체형 |

---

## 4. API 엔드포인트

### 4.1 논문 등록 (단건)

```http
POST http://localhost:8000/papers
Content-Type: application/json

{
  "device_info_id": 1,
  "treatment_id": 15,
  "doi": "10.1016/j.jaad.2024.01.023",
  "title": "High-Intensity Focused Ultrasound for Noninvasive Facial Rejuvenation",
  "title_ko": "비침습적 안면 회춘을 위한 고강도 집속 초음파",
  "authors": "Kim JH, Park SY, Lee MJ",
  "journal": "Journal of the American Academy of Dermatology",
  "pub_year": 2024,
  "abstract_summary": "본 연구는 HIFU(고강도 집속 초음파)의 안면 리프팅 효과를 평가한 무작위 대조 시험이다. 120명의 참가자를 대상으로 6개월 추적 관찰한 결과, HIFU 시술군에서 피부 탄력이 평균 32% 개선되었으며, 환자 만족도는 87%에 달했다. 부작용은 일시적인 홍반(12%)과 부종(8%)으로 대부분 48시간 내 소실되었다.",
  "key_findings": "- HIFU 시술 후 피부 탄력 평균 32% 개선 (p<0.001)\n- 환자 만족도 87% (매우 만족 42%, 만족 45%)\n- 효과 지속 기간: 평균 6개월 (4~9개월 범위)\n- 부작용: 일시적 홍반 12%, 부종 8% (48시간 내 소실)\n- SMAS층 도달 깊이 4.5mm에서 최적 효과",
  "keywords": "[\"HIFU\", \"울쎄라\", \"리프팅\", \"안면 회춘\", \"비침습\"]",
  "evidence_level": 4,
  "study_type": "RCT",
  "sample_size": "120명",
  "source_url": "https://pubmed.ncbi.nlm.nih.gov/38123456",
  "source_file": "papers/hifu_facial_2024.pdf",
  "status": "reviewed"
}
```

### 4.2 일괄 등록 (외부 프로그램 연동)

```http
POST http://localhost:8000/papers/bulk
Content-Type: application/json

[
  { "title": "논문1...", ... },
  { "title": "논문2...", ... }
]
```

**응답**: `{"created": 2, "message": "2건 논문이 등록되었습니다"}`

### 4.3 조회

```http
# 전체 목록
GET /papers

# 검색
GET /papers?q=울쎄라

# 장비별
GET /papers/by-device/1      # device_info_id=1 (울쎄라피 프라임)

# 시술별
GET /papers/by-treatment/15  # treatment_id=15 (울쎄라)

# 상태별
GET /papers?status=reviewed
```

---

## 5. 논문 분석 프로그램 구현 가이드

### 5.1 권장 처리 파이프라인

```
Step 1: PDF 텍스트 추출
    ├── PyMuPDF (fitz) — 빠르고 정확
    ├── pdfplumber — 테이블 추출에 강점
    └── OCR 필요시: pytesseract

Step 2: 메타데이터 추출
    ├── DOI 추출 (정규식: 10.\d{4,}/[\S]+)
    ├── 제목/저자/학술지 추출
    └── CrossRef API로 메타 보완 (DOI 기반)

Step 3: LLM 분석 (핵심)
    ├── 논문 요약 생성 (abstract_summary)
    ├── 핵심 발견 추출 (key_findings)
    ├── 근거 수준 판정 (evidence_level)
    ├── 연구 유형 분류 (study_type)
    ├── 키워드 추출 (keywords)
    └── 표본 크기 추출 (sample_size)

Step 4: 시술/장비 매칭
    ├── device_info 매칭 (이름 + aliases 비교)
    ├── evt_treatments 매칭 (이름 + brand 비교)
    └── 매칭 실패 시 → device_info_id=null, 수동 매칭

Step 5: API 전송
    └── POST /papers/bulk
```

### 5.2 LLM 프롬프트 예시

```python
ANALYSIS_PROMPT = """
다음 미용의료 논문을 분석하여 JSON 형식으로 응답해주세요.

## 논문 텍스트:
{paper_text}

## 출력 형식:
{{
  "title_ko": "한국어 제목 번역",
  "abstract_summary": "200~500자 한국어 요약. 연구 목적, 방법, 주요 결과, 결론을 포함",
  "key_findings": "핵심 발견 사항을 bullet point로 정리 (각 항목 앞에 - 붙여서). 수치 데이터 포함 필수",
  "keywords": ["키워드1", "키워드2", ...],
  "evidence_level": 0~5 사이 정수 (5=메타분석, 4=RCT, 3=코호트, 2=증례, 1=리뷰, 0=미분류),
  "study_type": "메타분석|RCT|전향적코호트|후향적코호트|증례시리즈|증례보고|전문가리뷰 중 택1",
  "sample_size": "참가자 수 (예: '120명')",
  "related_devices": ["논문에서 다루는 장비/시술명 리스트"]
}}

## 주의사항:
- abstract_summary는 반드시 한국어로 작성
- key_findings의 각 항목에는 가능한 p-value, 효과 크기 등 수치 포함
- evidence_level은 연구 설계에 따라 엄격하게 판정
- related_devices에는 논문에서 언급되는 장비/시술 브랜드명을 모두 나열
"""
```

### 5.3 시술/장비 매칭 로직

```python
def match_device(device_names: list[str], device_info_list: list[dict]) -> int | None:
    """
    논문에서 추출한 장비/시술명을 device_info 테이블과 매칭.
    device_info의 name + aliases를 모두 비교.
    """
    for device in device_info_list:
        # name 직접 매칭
        if device["name"] in device_names:
            return device["id"]
        # aliases 매칭
        if device.get("aliases"):
            for alias in device["aliases"].split(","):
                alias = alias.strip()
                if alias and alias in device_names:
                    return device["id"]
    return None
```

**매칭 우선순위:**
1. `device_info.name` 정확 매칭
2. `device_info.aliases` 매칭 (쉼표 구분)
3. `evt_treatments.name` 매칭
4. 부분 문자열 매칭 (fuzzy)
5. 매칭 실패 → `null` (수동 매칭 대기)

### 5.4 Python 구현 뼈대

```python
"""
논문 분석 프로그램 — uni-portal papers DB 연동

사용법:
  python paper_analyzer.py papers/*.pdf
  python paper_analyzer.py --dir papers/
"""

import os
import json
import requests
from pathlib import Path

# ── 설정 ──
API_BASE = "http://localhost:8000"
# LLM_API_KEY = os.environ.get("ANTHROPIC_API_KEY")  # 또는 다른 LLM

def extract_text_from_pdf(pdf_path: str) -> str:
    """PDF에서 텍스트 추출"""
    import fitz  # PyMuPDF
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def extract_metadata_from_doi(doi: str) -> dict:
    """CrossRef API로 논문 메타데이터 조회"""
    resp = requests.get(f"https://api.crossref.org/works/{doi}")
    if resp.ok:
        data = resp.json()["message"]
        return {
            "title": data.get("title", [""])[0],
            "authors": ", ".join(
                f"{a.get('family', '')} {a.get('given', '')}"
                for a in data.get("author", [])
            ),
            "journal": data.get("container-title", [""])[0],
            "pub_year": data.get("published-print", {}).get("date-parts", [[None]])[0][0],
        }
    return {}

def analyze_with_llm(text: str) -> dict:
    """LLM으로 논문 분석 (구현 필요)"""
    # TODO: Claude API 또는 다른 LLM 호출
    # ANALYSIS_PROMPT에 text를 넣어 호출
    pass

def get_device_info_list() -> list[dict]:
    """uni-portal에서 장비 사전 조회"""
    resp = requests.get(f"{API_BASE}/equipment/device-info")
    return resp.json() if resp.ok else []

def get_treatments_list() -> list[dict]:
    """uni-portal에서 시술 사전 조회"""
    resp = requests.get(f"{API_BASE}/events/treatments")
    return resp.json() if resp.ok else []

def match_device_id(related_devices: list[str]) -> int | None:
    """장비명으로 device_info_id 매칭"""
    devices = get_device_info_list()
    for name in related_devices:
        name_lower = name.lower().strip()
        for d in devices:
            if name_lower == d["name"].lower():
                return d["id"]
            for alias in (d.get("aliases") or "").split(","):
                if alias.strip().lower() == name_lower:
                    return d["id"]
    return None

def match_treatment_id(related_devices: list[str]) -> int | None:
    """시술명으로 treatment_id 매칭"""
    treatments = get_treatments_list()
    for name in related_devices:
        name_lower = name.lower().strip()
        for t in treatments:
            if name_lower == t["name"].lower():
                return t["id"]
    return None

def process_pdf(pdf_path: str) -> dict:
    """PDF 1건 처리 → papers 데이터"""
    text = extract_text_from_pdf(pdf_path)

    # DOI 추출
    import re
    doi_match = re.search(r'10\.\d{4,}/[\S]+', text)
    doi = doi_match.group() if doi_match else ""

    # 메타데이터
    meta = extract_metadata_from_doi(doi) if doi else {}

    # LLM 분석
    analysis = analyze_with_llm(text)

    # 장비/시술 매칭
    related = analysis.get("related_devices", [])
    device_info_id = match_device_id(related)
    treatment_id = match_treatment_id(related)

    return {
        "device_info_id": device_info_id,
        "treatment_id": treatment_id,
        "doi": doi,
        "title": meta.get("title", analysis.get("title", "")),
        "title_ko": analysis.get("title_ko", ""),
        "authors": meta.get("authors", ""),
        "journal": meta.get("journal", ""),
        "pub_year": meta.get("pub_year"),
        "abstract_summary": analysis.get("abstract_summary", ""),
        "key_findings": analysis.get("key_findings", ""),
        "keywords": json.dumps(analysis.get("keywords", []), ensure_ascii=False),
        "evidence_level": analysis.get("evidence_level", 0),
        "study_type": analysis.get("study_type", ""),
        "sample_size": analysis.get("sample_size", ""),
        "source_url": f"https://doi.org/{doi}" if doi else "",
        "source_file": str(pdf_path),
        "status": "draft",
    }

def upload_papers(papers: list[dict]):
    """uni-portal에 일괄 등록"""
    resp = requests.post(f"{API_BASE}/papers/bulk", json=papers)
    if resp.ok:
        print(f"등록 완료: {resp.json()}")
    else:
        print(f"등록 실패: {resp.status_code} {resp.text}")

# ── 실행 ──
if __name__ == "__main__":
    import sys
    pdf_files = sys.argv[1:] or list(Path("papers").glob("*.pdf"))

    results = []
    for pdf in pdf_files:
        print(f"분석 중: {pdf}")
        paper = process_pdf(str(pdf))
        results.append(paper)
        print(f"  → {paper['title_ko'] or paper['title']}")

    if results:
        upload_papers(results)
```

---

## 6. 데이터 품질 관리

### 6.1 상태(status) 워크플로우

```
draft → reviewed → verified
  │        │
  └── deleted (삭제 표시, 실제 삭제 안 함)
```

| 상태 | 의미 |
|------|------|
| `draft` | 자동 분석 완료, 검수 전 |
| `reviewed` | 1차 검토 완료 |
| `verified` | 최종 확인, 서비스 노출 가능 |
| `deleted` | 삭제 처리 (조회 제외) |

### 6.2 수동 검수 포인트

- [ ] `device_info_id` / `treatment_id` 매칭 정확성
- [ ] `abstract_summary` 내용 정확성
- [ ] `key_findings` 수치 데이터 검증
- [ ] `evidence_level` 연구 설계에 맞는지
- [ ] 중복 논문 여부 (DOI 기준)

---

## 7. 프론트엔드 연동 (예정)

논문 데이터가 쌓이면 **EquipmentView 상세 패널**의 `[P] 관련 논문` 섹션에서 표시:

```
GET /papers/by-device/{device_info_id}
```

표시 정보:
- 논문 제목 (한국어)
- 근거 수준 배지 (★★★★★)
- 연구 유형
- 핵심 발견 (접기/펼치기)
- 원문 링크

---

## 8. 의존성 (논문 분석 프로그램)

```txt
# PDF 처리
PyMuPDF>=1.24.0        # pip install pymupdf
pdfplumber>=0.11.0     # 테이블 추출 (선택)

# LLM (택 1)
anthropic>=0.39.0      # Claude API
# openai>=1.50.0       # GPT API

# 유틸
requests>=2.31.0       # API 호출
```

---

## 9. 빠른 시작

```bash
# 1. uni-portal API 실행 확인
curl http://localhost:8000/health
# → {"status":"ok"}

# 2. 장비 사전 확인
curl http://localhost:8000/equipment/device-info | python -m json.tool | head -20

# 3. 테스트 논문 등록
curl -X POST http://localhost:8000/papers \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Paper",
    "title_ko": "테스트 논문",
    "abstract_summary": "테스트용 논문 요약입니다.",
    "evidence_level": 0,
    "status": "draft"
  }'

# 4. 등록 확인
curl http://localhost:8000/papers
```
