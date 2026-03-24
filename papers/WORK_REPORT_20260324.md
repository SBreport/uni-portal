# 논문 분석 DB화 작업 리포트

- 작업일: 2026-03-24
- 작업자: Claude AI (자동 분석)
- DB 위치: `data/equipment.db` > `papers` 테이블
- 원본 폴더: `C:\LocalGD\0_INBOX\06_논문 분석\`

---

## 1. 전체 요약

| 항목 | 수량 |
|------|------|
| DB 저장 논문 | **180건** |
| 매칭 장비 수 | **23개** |
| 비학술 스킵 | **약 57건** |
| 장비 매칭률 | **100%** (미매칭 0건) |

## 2. 폴더별 처리 현황

| 폴더 | PDF수 | 저장 | 스킵 | 비고 |
|------|-------|------|------|------|
| 레디어스(멀츠) | 9 | **7** | 2 |  |
| 루카스 | 3 | **3** | 0 |  |
| 리바이브(멀츠) | 6 | **6** | 0 | 벨로테로 장비에 매칭 |
| 리쥬란 | 17 | **17** | 0 |  |
| 벨로테로(멀츠) | 20 | **14** | 6 | 마케팅자료4+중복1+요약1 스킵 |
| 슈링크(클래시스) | 17 | **3** | 14 | 14건 D&PS 매거진/홍보 스킵, 저장분은 볼뉴머 매칭 |
| 써마지 | 3 | **0** | 3 | 전부 비학술(브로셔/가이드/논문목록) |
| 아그네스 | 20 | **19** | 1 | 독일어 중복 1건 스킵 |
| 아포지, 피코슈어 | 9 | **8** | 1 | 제조사 백서 1건 스킵, 전부 피코슈어 매칭 |
| 에어녹스 | 26 | **12** | 14 | 비학술/스캔PDF/중복 14건 스킵 |
| 에토좀 PTT | 3 | **3** | 0 | 플래티넘PTT 매칭 |
| 엘라비에 리투오 | 11 | **10** | 1 | 중복 1건 스킵, 리투오 매칭 |
| 올리지오, 올리지오X, 피코 | 13 | **4** | 9 | 마케팅/영업자료/기업보고서 9건 스킵 |
| 인모드 | 12 | **6** | 6 | 교육자료/사용법/스캔PDF 등 스킵 |
| 젠틀맥스 프로플러스 | 15 | **12** | 3 | 요약집/스캔PDF/중복 3건 스킵 |
| 쥬베룩 | 29 | **27** | 2 | supplementary 2건 본논문에 포함 |
| 쥬비덤 | 4 | **4** | 0 |  |
| 콘셀티나(동방메디컬) | 1 | **1** | 0 | PDO 실 비교, 장비 신규등록 |
| 클라리티2(루트로닉) | 6 | **5** | 1 | 마케팅 포토북 1건 스킵 |
| 포텐자 | 7 | **7** | 0 | 전부 기초연구(Lv.0) |
| 피코플러스(루트로닉) | 6 | **5** | 1 | 중복파일 1건 스킵 |

## 3. 장비별 논문 수

| 장비 (device_info) | ID | 논문 수 |
|-------------------|-----|--------|
| 더마브이 | 62 | 6 |
| 레디어스 | 24 | 7 |
| 루카스 | 30 | 3 |
| 리쥬란 | 10 | 17 |
| 리투오 | 27 | 10 |
| 바디인모드 | 6 | 4 |
| 벨로테로 | 29 | 20 |
| 볼뉴머 | 13 | 3 |
| 써마지FLX | 2 | 1 |
| 아그네스 | 23 | 19 |
| 에어녹스 | 128 | 12 |
| 올리지오X | 12 | 4 |
| 인모드 | 5 | 2 |
| 젠틀맥스 | 36 | 1 |
| 젠틀맥스 프로 플러스 | 63 | 11 |
| 쥬베룩 | 11 | 27 |
| 쥬비덤 | 57 | 4 |
| 콘셀티나 | 129 | 1 |
| 클라리티2 | 7 | 5 |
| 포텐자 | 19 | 7 |
| 플래티넘PTT | 18 | 3 |
| 피코슈어 | 21 | 8 |
| 피코플러스 | 22 | 5 |

## 4. 근거 수준 분포

| Level | 유형 | 건수 |
|-------|------|------|
| 0 | 기초/전임상 | 22 |
| 1 | 체계적문헌고찰 | 20 |
| 2 | 증례보고/시리즈 | 49 |
| 3 | 코호트/관찰 | 43 |
| 4 | RCT | 32 |
| 5 | 설문/기타 | 14 |

## 5. 비학술 자료 스킵 상세

### 레디어스(멀츠)
- 리플렛 업뎃 260105.pdf (원내비치용 리플렛)
- 레디어스 리셋 브로셔 (2026).pdf (제품 브로셔)

### 벨로테로(멀츠)
- Biomimetic HCP 디테일 자료 1~3번 + 통합버전 (마케팅 4건)
- Micheels P et al 2017_JCAD.pdf (중복)
- 벨로테로 Purity 논문 요약_최종.pdf (한국어 요약 정리물)

### 슈링크(클래시스)
- D&PS 매거진 기사/인터뷰/경험담 (11건)
- The Aesthetic Guide 홍보 기사 (2건)
- VOLNEWMER 대한피부과의사회지 광고 (1건)

### 써마지
- Article list.pdf (논문 목록)
- 써마지 peer group 논문 브로셔.pdf (마케팅 브로셔)
- 써마지 FLX 시술참조가이드.pdf (사용 가이드)

### 아포지, 피코슈어
- Histology White Paper (Cynosure 백서)

### 에어녹스
- 브로셔/상담바인더/시술가이드 (비학술 3건)
- 허가 및 인증 문서 (6건)
- 스캔PDF 텍스트추출불가 3건
- 중복 1건, 교과서 발췌 요약 1건

### 엘라비에 리투오
- 제품 소개 자료.pptx
- 메가덤 논문 리스트.xlsx
- 논문 주요 내용 요약.pptx

### 올리지오, 올리지오X, 피코
- 올리지오X 마케팅 자료 4건 (Case Book/Ref Guide/Key-point/Sales Pres)
- 올리지오 마케팅 자료 3건 (Ref Guide 2건 + Sales Pres)
- Picocare 논문 요약집 (제조사 편집)
- 원텍 올리지오X 전임상 결과보고서 (비공개 기업 보고서)

### 인모드
- body FX 교육자료/인모드 RF 교육자료/인모드+바디 교육자료 (3건)
- 인모드핸드피스 세척법.pdf / 포마-미니 가이드.pdf
- BodyFX/MiniFX 스캔PDF (텍스트추출불가)
- MiniFX mechanisms.pptx / 비포애프터 jpg 28장 / mp4 3개

### 젠틀맥스 프로플러스
- Gentle Laser Family 논문 요약본.pdf (제조사 편집)
- 스캔PDF 텍스트추출불가 1건
- 중복 파일 1건

### 클라리티2(루트로닉)
- CLARITY2_PHOTOBOOK.pdf (마케팅 포토북)

### 피코플러스(루트로닉)
- 중복 파일 1건 (동일 논문 2개 PDF)

## 6. 비PDF 파일 기록

| 폴더 | 파일명 | 유형 | 비고 |
|------|--------|------|------|
| 아그네스 | Article list.xlsx | xlsx | 논문 목록 |
| 에어녹스 | 홈페이지이미지/ (00~04.jpg, Q&A.jpg) | jpg x6 | 제품 이미지 |
| 에어녹스 | 아산화질소와 흡입마취제.docx | docx | 참고문서 |
| 엘라비에 리투오 | Elravie Re2O_제품 소개 자료.pptx | pptx | 제품소개 |
| 엘라비에 리투오 | L&C BIO_메가덤 논문 리스트.xlsx | xlsx | 논문목록 |
| 엘라비에 리투오 | 엘라비에 리투오 논문 주요 내용 요약.pptx | pptx | 논문요약 |
| 인모드 | 비포애프터/ (Forma, BodyFX, MiniFX, Fractora) | jpg x28 | 시술 전후 사진 |
| 인모드 | FORMA/MiniFX/핸드피스관리법 | mp4 x3 | 교육 영상 |
| 인모드 | MiniFX mechanisms.pptx | pptx | 기전 설명 |
| 쥬베룩 | 논문_파일명_개요.xlsx | xlsx | 논문목록 |
| 포텐자 | 포텐자 논문.txt | txt | 논문 URL 목록 |

## 7. 특이사항

- **써마지**: 폴더 내 PDF 3건 전부 비학술 자료 -> 학술 논문 0건 저장
- **아포지**: 폴더명에 포함되어 있으나 실제 PDF는 전부 피코슈어 관련 (아포지 논문 0건)
- **에어녹스**: N2O 진정기 장비가 기존 DB에 미등록 -> 신규 등록 (id=128) 후 12건 매칭
- **콘셀티나**: 논문에 제품명 미언급 -> 장비 신규 등록 (id=129) 후 매칭
- **인모드 비포애프터 사진 28장**: Forma/BodyFX/MiniFX/Fractora 시술 전후 사진
- **슈링크 폴더**: 저장된 3건은 실제로 볼뉴머(id=13) RF 논문에 해당
- **더마브이 폴더**: 이전 세션에서 작업 완료 (이번 세션에서 HIFU 1건 매칭 보정)

## 8. 전체 논문 목록 (180건)

| ID | 장비 | 제목 | 학술지 | 연도 | 유형 | Lv |
|-----|------|------|--------|------|------|----|
| 21 | 더마브이 | HIFU 시술에 의한 조직 응고 변화를 적외선 열화상 이미징으로 정량화한 기초 연구 | Korean Journal of Optics  | 2017 | 기초연구(in vitro/e | 0 |
| 22 | 더마브이 | 더마브이 KTP레이저(532nm)와 브이빔 펄스다이레이저(595nm)를 이용한 주사비 치료... | Journal of Cosmetic Derma | 2024 | 비무작위대조시험 | 4 |
| 23 | 더마브이 | 포트와인 모반(적자색 혈관기형) 치료를 위한 532nm KTP 레이저와 595nm 펄스 다... | 미기재 |  | RCT | 4 |
| 24 | 더마브이 | 혈관 및 색소 병변 치료를 위한 신형 가변 순차 장펄스 532nm/1064nm 레이저의 안... | Dermatologic Surgery | 2023 | 전향적코호트 | 3 |
| 25 | 더마브이 | 냉각 스프레이를 적용한 새로운 532nm 가변 펄스 구조 이중 파장 KTP 레이저의 주사비... | Lasers in Surgery and Med | 2023 | 증례시리즈 | 2 |
| 26 | 더마브이 | 혈관 질환 치료를 위한 새로운 가변 시퀀스 장펄스 532nm/1064nm 레이저의 임상 및... | Dermatologic Surgery | 2024 | 증례시리즈 | 2 |
| 27 | 레디어스 | 칼슘하이드록실아파타이트(CaHA, 레디어스) 미세입자의 섬유아세포 직접 접촉을 통한 신생콜... | Journal of Cosmetic Derma | 2023 | 기초연구(in vitro/e | 0 |
| 28 | 레디어스 | 아시아 환자를 위한 칼슘하이드록실아파타이트(CaHA, 레디어스) 최적 사용법: 얼굴 및 바... | Journal of Clinical and A | 2021 | 전문가합의(Delphi) | 1 |
| 29 | 레디어스 | 희석 및 고희석 칼슘하이드록실아파타이트(CaHA, 레디어스)를 이용한 피부 타이트닝: 글로... | Dermatologic Surgery | 2018 | 전문가합의(Delphi) | 1 |
| 30 | 레디어스 | 칼슘하이드록실아파타이트(CaHA, 레디어스)의 재생미용 치료제로서의 역할: 내러티브 리뷰 | Aesthetic Surgery Journal | 2023 | 내러티브리뷰 | 1 |
| 31 | 레디어스 | 고희석 칼슘하이드록실아파타이트(CaHA, 레디어스)의 안면 및 바디 바이오스티뮬레이션: 브... | Plastic and Reconstructiv | 2019 | 전문가합의(Delphi) | 1 |
| 32 | 레디어스 | 재생미용의 발전: 칼슘하이드록실아파타이트(CaHA, 레디어스) 중심 리뷰 및 증례 시리즈 | Cureus | 2025 | 증례시리즈 | 2 |
| 33 | 레디어스 | 희석 칼슘하이드록실아파타이트(CaHA, 레디어스)의 목 및 데콜테 주입 후 신생콜라겐 생성... | Journal of Drugs in Derma | 2017 | 전향적코호트 | 3 |
| 34 | 루카스 | IPL(고강도 펄스광)과 저출력 Q-스위치 Nd:YAG 레이저 병합 치료의 기미 환자 적용... | Annals of Dermatology | 2012 | 증례시리즈 | 2 |
| 35 | 루카스 | 저출력 1064nm Q-스위치 Nd:YAG 레이저를 이용한 기미 치료: 아시안 환자 50명... | Journal of Dermatological | 2013 | 전향적코호트 | 3 |
| 36 | 루카스 | 펄스형 염료 레이저(PDL)와 1,064nm Q-스위치 Nd:YAG 레이저를 이용한 기미 ... | Annals of Dermatology | 2018 | RCT | 4 |
| 95 | 리쥬란 | 고순도 폴리뉴클레오타이드(PN)의 건조하고 갈라진 입술 치료에 대한 임상적 효능 및 안전성... | Journal of Cosmetic Derma | 2025 | 전향적 다기관 관찰연구 | 3 |
| 96 | 리쥬란 | 33MHz 초음파를 이용한 안면 10개 부위의 진피 두께 분석 및 Rejumate 자동 주... | PRS Global Open | 2025 | 후향적 관찰연구 | 4 |
| 97 | 리쥬란 | 튼살(팽창선조) 치료에서 폴리뉴클레오타이드(PN), 프랙셔널 CO2 레이저, 및 병합 요법... | Archives of Dermatologica | 2025 | 전향적 무작위 피험자 내 대 | 2 |
| 98 | 리쥬란 | 수분 분포 모델을 이용한 폴리뉴클레오타이드(PN) 피내 주사 후 진피의 수분 보유 능력 평... | Journal of Cosmetic Derma | 2025 | 파일럿 실험연구(대조군 포함 | 4 |
| 99 | 리쥬란 | 폴리뉴클레오타이드(PN) 스킨부스터를 이용한 혁신적 입술 부스팅 기법 | PRS Global Open | 2025 | 증례보고(Case repor | 5 |
| 100 | 리쥬란 | 안드로겐성 탈모(AGA)에서 폴리뉴클레오타이드(PN)의 새로운 치료적 접근: 전향적 파일럿... | Archives of Dermatologica | 2025 | 전향적 파일럿 연구(단일군) | 3 |
| 101 | 리쥬란 | 장쇄 폴리뉴클레오타이드(PN) 필러를 이용한 피부 재생: 5명 환자에서의 효능 및 합병증 | Dermatologic Therapy | 2016 | 증례보고(Case serie | 5 |
| 102 | 리쥬란 | 1,064nm 프랙셔널 피코초 레이저와 폴리뉴클레오타이드(PN) 겔 주사를 이용한 이마 전... | Medical Lasers; Engineeri | 2018 | 증례보고(Case repor | 5 |
| 103 | 리쥬란 | 갑상선절제술 후 흉터에 대한 폴리뉴클레오타이드(PN)의 예방 효과: 무작위, 이중맹검, 대... | Lasers in Surgery and Med | 2018 | 무작위 이중맹검 대조 임상시 | 2 |
| 104 | 리쥬란 | 폴리뉴클레오타이드(PN)와 히알루론산(HA) 필러의 눈 주위 피부 재생 효과 비교: 무작위... | Journal of Dermatological | 2020 | 무작위 이중맹검 반안면(sp | 2 |
| 105 | 리쥬란 | 주사용 폴리뉴클레오타이드(PN)의 미용 사용에 관한 설문조사: 한국 피부과 전문의의 진료 ... | Journal of Cosmetic Derma | 2023 | 설문조사 연구(Survey) | 5 |
| 106 | 리쥬란 | 미용 의사들의 안면 홍반 치료를 위한 폴리뉴클레오타이드(PN) 사용 현황과 효과 인식에 관... | Skin Research and Technol | 2023 | 설문조사 연구(Survey) | 5 |
| 107 | 리쥬란 | 의인성 지방 위축 2명 환자에서의 폴리뉴클레오타이드(PN) 주사 치료: 미용의료에서의 안전... | Skin Research and Technol | 2023 | 증례보고(Case repor | 5 |
| 108 | 리쥬란 | DOT 폴리뉴클레오타이드(PN)의 고해상도 3D 주사전자현미경(SEM) 이미지: 고유한 스... | Skin Research and Technol | 2024 | 기초 실험연구(in vitr | 5 |
| 109 | 리쥬란 | 미용 시술 의사들의 확대된 안면 모공에 대한 주사용 폴리뉴클레오타이드(PN) 사용 현황과 ... | Skin Research and Technol | 2024 | 설문조사 연구(Survey) | 5 |
| 110 | 리쥬란 | 폴리뉴클레오타이드(PN)와 히알루론산 복합 피내 주사의 안면 홍반에 대한 임상 효과: PN... | Skin Research and Technol | 2024 | 후향적 증례보고(Case r | 5 |
| 111 | 리쥬란 | 전투 부상 포함 다양한 안면 흉터에 대한 폴리뉴클레오타이드(PN) 기반 치료 | Journal of Dermatological | 2024 | 증례 시리즈(Case ser | 5 |
| 190 | 리투오 | 무세포 진피 기질(ADM)의 두께와 표면적이 직접-임플란트 유방재건에 미치는 영향 | Gland Surgery | 2022 | Retrospective C | 3 |
| 191 | 리투오 | 감염된 유방 임플란트 구제 전략: 7명의 연속 환자 회복 사례로부터의 교훈 | Archives of Plastic Surge | 2021 | Case Series | 2 |
| 192 | 리투오 | 전대흉근 전방 텐팅법을 이용한 로봇보조 유방재건술 | Journal of Plastic, Recon | 2021 | Case Series | 2 |
| 193 | 리투오 | 임플란트 기반 즉시 유방재건에서 멸균 무세포 진피 기질 사용이 합병증 발생률에 미치는 영향 | Archives of Plastic Surge | 2016 | Retrospective C | 3 |
| 194 | 리투오 | 마우스 모델에서 무세포 진피 기질/히알루론산 필러와 자가 지방이식의 부피 유지율 및 생체적... | Aesthetic Plastic Surgery | 2020 | Animal Study (B | 0 |
| 195 | 리투오 | 종양성형 유방보존수술에서 절단된 무세포 진피 기질을 이용한 부피 대체: 전향적 단일기관 경... | World Journal of Surgical | 2020 | Prospective Coh | 3 |
| 196 | 리투오 | 미세화 가교결합 인체 무세포 진피 기질: 콜라겐 합성에 효과적인 지지체이자 유망한 조직 보... | Tissue Engineering and Re | 2017 | Animal Study (B | 0 |
| 197 | 리투오 | 가교결합 인체 무세포 진피 기질의 특성 분석 및 조직 통합 | Biomaterials | 2015 | Animal Study (B | 0 |
| 198 | 리투오 | 미세화 무세포 진피 기질 필러를 이용한 선형 경피증(en Coup de Sabre) 치료:... | Annals of Dermatology | 2021 | Case Report | 2 |
| 199 | 리투오 | 히알루론산/미세화 가교결합 무세포 진피 기질 필러를 이용한 HIV 관련 안면 지방위축 치료 | Journal of Korean Medical | 2022 | Prospective Ope | 3 |
| 132 | 바디인모드 | 비수술 체형 교정: 흡입 결합 RF 가열과 초단펄스 고전압을 이용한 비침습 국소 지방 감소... | Journal of Clinical & Exp | 2012 | 전향적 코호트 연구(pros | 3 |
| 133 | 바디인모드 | 신규 비침습 고주파 장비를 이용한 지방조직 장기 감소의 임상적 및 생물학적 평가 | Lasers in Surgery and Med | 2014 | 전향적 코호트 연구 + 조직 | 3 |
| 134 | 바디인모드 | 파이롭토시스: 지방세포의 새로운 세포 사멸 메커니즘 | QMP's Plastic Surgery Pul | 2015 | 전문가 리뷰/해설(exper | 1 |
| 135 | 바디인모드 | 지방의 파이롭토시스: BodyFX 치료와 세포 사멸 메커니즘 | Body Language (Equipment  | 2016 | 전문가 리뷰/해설(exper | 1 |
| 37 | 벨로테로 | HA 필러의 혈관 내 분산 및 파편화에 대한 겔 물성 매개변수의 영향: 동맥 색전증(혈관 ... | Gels | 2024 | 체외실험연구 | 5 |
| 38 | 벨로테로 | 히알루론산(HA) 스킨부스터와 필러의 물리화학적 물성 비교를 통한 제품 분류 연구 | Journal of Cosmetic Derma | 2022 | 체외비교연구 | 5 |
| 39 | 벨로테로 | 주사형 히알루론산(HA) 스킨부스터 5종의 물리화학적 물성 비교 연구 | Macromolecular Materials  | 2021 | 체외비교연구 | 5 |
| 40 | 벨로테로 | 벨로테로 리바이브(CPM-HA20G) 시술 후 안면 피부질 개선 효과: 한국인 임상 경험 | Journal of Cosmetic Derma | 2025 | 전향적단일군연구 | 4 |
| 41 | 벨로테로 | 벨로테로 리바이브(CPM-HA20G)의 안면 피부 재생 효과: 다기관 무작위 연구 (다회 ... | Plastic and Reconstructiv | 2021 | 다기관무작위비교연구 | 2 |
| 42 | 벨로테로 | 벨로테로 리바이브(CPM-HA20G)의 안면 피부 재생 효과: 효과적이고 안전한 조기 미용... | Clinical, Cosmetic and In | 2019 | 전향적단일군연구 | 4 |
| 116 | 벨로테로 | 벨로테로 밸런스의 주요 안전성 및 유효성 임상시험 종합 리뷰 | Plastic and Reconstructiv | 2013 | 체계적문헌고찰 | 1 |
| 117 | 벨로테로 | 15종 히알루론산 필러의 지연 반응에 대한 문헌 리뷰 | Dermatologic Surgery | 2022 | 체계적문헌고찰 | 2 |
| 118 | 벨로테로 | 히알루론산 필러 내 불용성 입자 불순물의 면역학적 영향 탐구: CPM(응집성 다밀도 매트릭... | Clinical, Cosmetic and In | 2026 | 실험실연구+인체조직학 | 3 |
| 119 | 벨로테로 | 표재성 망상 진피 주입을 위한 두 가지 가교 기술 비교: 초음파 및 조직학적 연구 | Journal of Clinical and A | 2017 | 비교실험연구 | 3 |
| 120 | 벨로테로 | 두 종류의 볼류마이징 히알루론산 필러의 유효성 비교: 대조, 무작위, 이중맹검, 분할 안면... | Clinical, Cosmetic and In | 2017 | 무작위대조시험 | 2 |
| 121 | 벨로테로 | 모든 주사용 피부 필러 시술 후 발생하는 이물질 육아종: 제1부 - 가능한 원인 | Plastic and Reconstructiv | 2009 | 전문가리뷰 | 4 |
| 122 | 벨로테로 | CPM(응집성 다밀도 매트릭스) 가교 히알루론산 볼류마이징 겔: MRI 및 CT 영상 연구 | Clinical, Cosmetic and In | 2019 | 증례보고 | 4 |
| 123 | 벨로테로 | 피부 필러 사용 후 이물질 육아종: 병태생리, 임상 양상, 조직학적 특징 및 치료 | Archives of Plastic Surge | 2015 | 종설 | 4 |
| 124 | 벨로테로 | 리도카인 함유 CPM(응집성 다밀도 매트릭스) 히알루론산 필러의 임상 환경에서의 안전성 및... | Clinical, Cosmetic and In | 2016 | 전향적관찰연구 | 3 |
| 125 | 벨로테로 | 히알루론산 필러를 이용한 수평 목주름 치료: 후향적 증례 연구 | Plastic and Reconstructiv | 2019 | 후향적증례연구 | 4 |
| 126 | 벨로테로 | 2년간 전내측 볼 부위 히알루론산 필러의 볼륨 증강 및 지속 변화에 대한 정량적 평가 | Plastic and Reconstructiv | 2022 | 전향적비교연구 | 3 |
| 127 | 벨로테로 | CPM(응집성 다밀도 매트릭스) 히알루론산 겔을 이용한 볼륨 증강의 실제 임상 경험 | Journal of Clinical and A | 2018 | 후향적관찰연구 | 4 |
| 128 | 벨로테로 | 중안면 볼륨 증강을 위한 히알루론산 필러의 시간 경과에 따른 변화 비교: 분할 안면 연구 | Dermatologic Therapy | 2019 | 전향적비교연구 | 3 |
| 129 | 벨로테로 | 집속 초음파, CPM 히알루론산, 인코보툴리눔독소A를 이용한 수평 목주름의 복합 치료 접근... | Dermatologic Surgery | 2019 | 전향적단일군연구 | 4 |
| 43 | 볼뉴머 | 모노폴라 고주파 팁 크기에 따른 안면 회춘 효과의 반얼굴 비교 연구 | Journal of Clinical and A | 2024 | RCT | 4 |
| 44 | 볼뉴머 | 연속 수냉식 모노폴라 고주파와 기존 냉매 분사 냉각식 모노폴라 고주파의 안면 회춘 효과 비... | Annals of Dermatology | 2025 | RCT | 4 |
| 45 | 볼뉴머 | 연속 수냉식 모노폴라 고주파의 피부 질감 및 탄력 개선 효과 평가: 주름 감소와 피부 리프... | Plastic and Reconstructiv | 2024 | 전향적코호트 | 3 |
| 18 | 써마지FLX | 4세대 비침습적 독극성 고주파의 피부 탄력 개선 시술: 델파이 전문가 합의 | Journal of Drugs in Derma | 2020 | 전문가합의(Delphi) | 1 |
| 148 | 아그네스 | 고주파 교류 전류: 선택적 전자기 조직 반응 | Medical Lasers; Engineeri | 2016 | 내러티브리뷰 | 1 |
| 149 | 아그네스 | 필러 주입 후 발생한 함몰 흉터를 공압식 무침 주사기와 고주파 장비로 성공적으로 치료한 증... | Dermatologic Therapy | 2016 | 증례보고 | 2 |
| 150 | 아그네스 | 주름 치료를 위한 고주파 장비의 임상 경험 및 효능 | Lasers in Medical Science | 2017 | 증례시리즈 | 2 |
| 151 | 아그네스 | 토끼 귀 모델에서 절연 미세침 고주파를 이용한 여드름 치료를 위한 피지선 표적 파괴 | Lasers in Surgery and Med | 2017 | 동물실험 | 0 |
| 152 | 아그네스 | 고주파 장비로 성공적으로 치료한 국소 재발성 입술 혈관부종 | Journal of Clinical & Inv | 2017 | 증례보고 | 2 |
| 153 | 아그네스 | 단침 고주파 장비를 이용한 천연두 흉터의 성공적 치료 | International Wound Journ | 2017 | 증례보고 | 2 |
| 154 | 아그네스 | 레이저 및 에너지 기반 장비를 이용한 하안검 지방 돌출의 수술적/비수술적 치료 | Medical Lasers; Engineeri | 2017 | 내러티브리뷰 | 1 |
| 155 | 아그네스 | 절연 단극 고주파 미세침 장비를 이용한 비침습적 지방종 크기 축소 | International Journal of  | 2018 | 증례보고 | 2 |
| 156 | 아그네스 | 새로운 절연 단극 고주파 미세침 장비를 이용한 모낭상피종의 성공적 치료 | Clinical and Experimental | 2018 | 증례보고 | 2 |
| 157 | 아그네스 | 절연 미세침을 이용한 병변 내 전기응고술의 눈 주위 한관종 치료: 후향적 분석 | Aesthetic Surgery Journal | 2018 | 후향적코호트 | 3 |
| 158 | 아그네스 | 신증후군 환자에서 선택적 전기열분해술을 이용한 중증 여드름의 성공적 치료 | Annals of Dermatology | 2019 | 증례보고 | 2 |
| 159 | 아그네스 | 한관종 치료를 위한 절연 미세침 고주파와 이산화탄소 레이저 절제술의 비교 | Dermatologic Therapy | 2019 | 증례보고 | 2 |
| 160 | 아그네스 | 단침 절연 고주파 장비를 이용한 포다이스 반점의 성공적 치료 증례 | Dermatologic Therapy | 2019 | 증례보고 | 2 |
| 161 | 아그네스 | 여드름 환자에서 단침 고주파 장비를 이용한 선택적 피지선 전기열분해술: 전향적 무작위 대조... | Lasers in Surgery and Med | 2019 | RCT | 4 |
| 162 | 아그네스 | 눈 주위 주름 치료를 위한 미세침 단극 고주파의 효능 및 안전성 | Journal of Dermatological | 2019 | 후향적코호트 | 3 |
| 163 | 아그네스 | 하안검 지방 돌출 치료를 위한 절연 미세침 고주파 시스템의 효능 | Journal of the German Soc | 2019 | 전향적코호트 | 3 |
| 164 | 아그네스 | 병변 내 절연 미세침 고주파 장비로 치료한 포다이스 반점 | Medical Lasers; Engineeri | 2021 | 증례보고 | 2 |
| 165 | 아그네스 | 이중턱 지방 감소를 위한 절연 미세침 고주파 장비의 효능 및 안전성 | Dermatologic Surgery | 2022 | 전향적코호트 | 3 |
| 166 | 아그네스 | 절연 단극 고주파 미세침 장비와 양자분자공명 장비의 병합으로 성공적으로 치료한 난치성 필러... | Medical Lasers; Engineeri | 2022 | 증례보고 | 2 |
| 175 | 에어녹스 | 아산화질소와 흡입마취제 | Anesthesia Progress | 2008 | Review | 1 |
| 176 | 에어녹스 | 현대 마취 실무에서의 아산화질소 | BJA Education | 2015 | Review | 1 |
| 177 | 에어녹스 | 피부과에서의 아산화질소 사용: 체계적 문헌고찰 | Dermatologic Surgery | 2017 | Systematic Revi | 5 |
| 178 | 에어녹스 | 개원의를 위한 치과진정법 근거기반 임상진료지침 개발 | Journal of Korean Academy | 2016 | Clinical Practi | 1 |
| 179 | 에어녹스 | 소아 치과치료에서 미다졸람 정주와 아산화질소 흡입진정법 병용의 특성 | Journal of the Korean Aca | 2020 | Retrospective C | 3 |
| 180 | 에어녹스 | 아산화질소 남용에 의한 척수의 아급성 연합변성 환자에서 비타민 B12 투여방법에 대한 체계... | Journal of the Korean Soc | 2019 | Systematic Revi | 1 |
| 181 | 에어녹스 | 아산화질소 농도 및 적용 방법에 따른 생리학적 변화 결정 | Journal of the Korean Aca | 2016 | Randomized Cont | 4 |
| 182 | 에어녹스 | 아산화질소가 후두경 및 기관내 삽관에 의한 심혈관계 반응에 미치는 영향 | Korean Journal of Anesthe | 2003 | Randomized Cont | 4 |
| 183 | 에어녹스 | 아산화질소(N2O)와 공기(Air)를 사용한 마취 수술의 기낭압 조정이 수술 후 인후통과 ... | Journal of Korean Academy | 2019 | Quasi-experimen | 3 |
| 184 | 에어녹스 | 임플란트 수술을 위한 미다졸람 정주와 아산화질소 흡입 병용 진정법의 효과와 안전성에 대한 ... | Journal of the Korean Den | 2012 | Prospective Ran | 4 |
| 185 | 에어녹스 | 진정법 가이드라인 소개와 진정전문의 필요성 | Journal of the Korean Aca | 2012 | Narrative Revie | 1 |
| 186 | 에어녹스 | 한양대학교 치과 진정요법클리닉에서의 진정요법(II) | Journal of the Korean Den | 2007 | Retrospective C | 2 |
| 112 | 올리지오X | 아시아인의 하안면 이완에 대한 단극 고주파(RF) 치료의 유효성 및 안전성 | Dermatology and Therapy ( | 2022 | 전향적 코호트 연구(pros | 3 |
| 113 | 올리지오X | 노화 안면 피부 타이트닝을 위한 단극 고주파(RF)의 유효성 및 안전성 | Cosmetics | 2024 | 전향적 평가자-맹검 코호트  | 3 |
| 114 | 올리지오X | 단극 고주파 장비의 에너지 전달 및 피부 타이트닝 유효성과 안전성 평가: 전임상-임상 번역... | Lasers in Medical Science | 2025 | 전임상(마이크로피그) + 전 | 3 |
| 115 | 올리지오X | 한국산 고주파 리프팅 장비의 기술 사양 비교 분석: 혁신과 글로벌 경쟁력을 중심으로 | Aesthetics (Korean Societ | 2025 | 기술 비교 리뷰(techni | 1 |
| 130 | 인모드 | 비침습 고주파(RF) 피부 타이트닝 장비의 임상 평가: Forma | Journal of Cosmetic and L | 2015 | 증례 시리즈(case ser | 2 |
| 131 | 인모드 | IPL을 이용한 피부 재생에서 피크 파워의 효과: Lumecca IPL 평가 | Advances in Aging Researc | 2016 | 증례 시리즈(case ser | 2 |
| 147 | 젠틀맥스 | 피츠패트릭 피부타입 IV-VI에서의 Nd:YAG 레이저 제모 | Journal of Drugs in Derma | 2013 | 전문가 경험 보고(exper | 1 |
| 136 | 젠틀맥스 프로 플러스 | 알렉산드라이트 레이저와 다이오드 레이저의 4회 시술 제모 비교: 1년 결과 | Dermatologic Surgery | 2001 | 무작위 대조 시험(RCT,  | 4 |
| 137 | 젠틀맥스 프로 플러스 | 레이저 제모: 755nm 알렉산드라이트 레이저의 장기 결과 | Dermatologic Surgery | 2001 | 후향적 코호트 연구(retr | 3 |
| 138 | 젠틀맥스 프로 플러스 | Gentlease 755nm 알렉산드라이트 레이저 제모에서 18mm vs 12mm 스팟 사... | Dermatologic Surgery | 2004 | 이중맹검 무작위 대조 시험( | 4 |
| 139 | 젠틀맥스 프로 플러스 | 알렉산드라이트 레이저와 IPL의 안면 제모 무작위 양측 비교 연구 | Lasers in Surgery and Med | 2007 | 무작위 양측 분할 대조 시험 | 4 |
| 140 | 젠틀맥스 프로 플러스 | 장펄스 알렉산드라이트와 Nd:YAG 레이저의 단독 및 병합 다리 제모 비교: 18개월 추적... | Archives of Dermatology | 2008 | 무작위, 피험자 내 대조,  | 4 |
| 141 | 젠틀맥스 프로 플러스 | 가성모낭염(면도 후 모낭염) 치료를 위한 장펄스 알렉산드라이트 레이저와 IPL의 1년 추적... | Indian Journal of Dermato | 2009 | 무작위 양측 분할 대조 시험 | 4 |
| 142 | 젠틀맥스 프로 플러스 | 지루각화증 치료에서 장펄스 755nm 알렉산드라이트 레이저의 치료 효과 | Journal of the European A | 2014 | 후향적 증례 시리즈(retr | 2 |
| 143 | 젠틀맥스 프로 플러스 | 특발성 다모증의 보완 치료: 감초(리코리스) 국소도포의 가능성 | Evidence-Based Complement | 2015 | 이중맹검 무작위 대조 시험( | 4 |
| 144 | 젠틀맥스 프로 플러스 | 겨드랑이 제모 레이저가 정상 미생물 균총에 미치는 영향 | Journal of Lasers in Medi | 2020 | 전향적 대조 임상시험(pro | 3 |
| 145 | 젠틀맥스 프로 플러스 | 사전 확장 두피 피판과 레이저 제모를 결합한 이마 재건술 | Journal of Craniofacial S | 2025 | 후향적 증례 시리즈(retr | 2 |
| 146 | 젠틀맥스 프로 플러스 | 경구개 요골 전완 유리피판 재건부의 장펄스 알렉산드라이트 레이저 제모 | JAAD Case Reports (예상) | 2025 | 증례 보고(case repo | 2 |
| 63 | 쥬베룩 | PDLLA(폴리-D,L-젖산) 필러가 노화 동물 피부에서 지방생성을 촉진하여 피하지방 조직... | International Journal of  | 2024 | 기초연구 (in vitro  | 0 |
| 64 | 쥬베룩 | PDLLA 주사를 이용한 안면 인대 두께 증가 | Journal of Cosmetic Derma | 2025 | 증례보고 (Clinical  | 2 |
| 65 | 쥬베룩 | 스킨부스터 주사 후 발생한 후허혈성 시신경병증 | Journal of Neuro-Ophthalm | 2024 | 증례보고 | 2 |
| 66 | 쥬베룩 | 리프팅 목적의 측두 지방 패드 필러 주사: 심부측두근막 표층의 이동 | Journal of Cosmetic Derma | 2025 | 증례보고 (Clinical  | 2 |
| 67 | 쥬베룩 | 위축성 여드름 흉터에 대한 폴리젖산의 무침 제트 주사: 문헌 고찰 및 증례 보고 | Journal of Clinical Medic | 2024 | 문헌고찰 + 증례보고 | 1 |
| 68 | 쥬베룩 | 아시아인에서 경피 마이크로젯 약물 전달을 통한 PDLLA 강화 위축성 흉터 치료 | Skin Research and Technol | 2024 | 증례 연구 (Case ser | 2 |
| 69 | 쥬베룩 | 마이크로니들 프랙셔널 고주파를 이용한 PDLLA의 진피 내 주입에 의한 여드름 흉터 치료:... | Dermatologic Surgery | 2022 | 전향적 공개 임상시험 | 3 |
| 70 | 쥬베룩 | PDLLA가 노화 동물 피부에서 혈관신생과 콜라겐 합성을 자극한다 | International Journal of  | 2023 | 기초연구 (in vitro  | 0 |
| 71 | 쥬베룩 | PDLLA 필러가 노화 피부에서 모낭줄기세포를 조절하여 모발 성장을 촉진한다 | Cells | 2026 | 기초연구 (in vitro  | 0 |
| 72 | 쥬베룩 | PDLLA 필러가 노화 관련 모낭 기능 저하를 개선하여 모발 두께와 윤기를 회복시킨다 | International Journal of  | 2026 | 기초연구 (in vitro  | 0 |
| 73 | 쥬베룩 | 하안검 회춘을 위한 PDLLA 평가: 효능과 안전성 | Journal of Cosmetic Derma | 2025 | 증례 연구 (Case ser | 2 |
| 74 | 쥬베룩 | 기미 치료를 위한 PDLLA 피하 주사의 효능 | Journal of Cosmetic Derma | 2024 | 증례보고 (Clinical  | 2 |
| 75 | 쥬베룩 | 레이저 구동 마이크로젯을 이용한 PDLLA 주입의 기미 및 광노화 개선 예비 평가 | Dermatologic Surgery | 2024 | 전향적 관찰 연구 | 3 |
| 76 | 쥬베룩 | PDLLA 스킨부스터의 진피 내 vs 피하 주사 통증 비교: 무작위 이중맹검 분할주사 연구 | Aesthetic Plastic Surgery | 2025 | 무작위 이중맹검 분할주사 연 | 4 |
| 77 | 쥬베룩 | PDLLA 필러가 기저막 파괴를 감소시켜 자외선B 유도 피부 색소침착을 완화한다 | International Journal of  | 2024 | 기초연구 (in vitro  | 0 |
| 78 | 쥬베룩 | 콜라겐 생체자극제가 광노화 색소침착을 개선한다 | Experimental Dermatology | 2024 | 무작위 반분면(split-f | 4 |
| 79 | 쥬베룩 | 마이크로니들링과 PDLLA(쥬베룩) 국소 도포 병합의 안면 모공 축소 및 피부 결 개선 효... | Plastic and Reconstructiv | 2025 | 증례 연구 (Case ser | 2 |
| 80 | 쥬베룩 | PDLLA와 비가교 히알루론산 복합제의 피부 회춘 효과: 예비 연구 | Journal of Cosmetic Derma | 2023 | 전향적 관찰 연구 | 3 |
| 81 | 쥬베룩 | 무침 레이저 주사기 vs 니들 주사의 진피 필러 피부 개선 및 회춘 효과 비교 | Lasers in Surgery and Med | 2023 | 전향적 무작위 반분면(spl | 4 |
| 82 | 쥬베룩 | 중등도 주사비(로자세아) 치료에서 캐뉼라 기법으로 투여한 PDLLA의 효능과 안전성 평가 | Plastic and Reconstructiv | 2025 | 증례 연구 (Case ser | 2 |
| 83 | 쥬베룩 | 주사비 치료에서의 PDLLA | Aesthetic Plastic Surgery | 2025 | 편집자 서신 (Letter  | 2 |
| 84 | 쥬베룩 | 아시아 환자에서 경피 마이크로젯 약물 전달을 통한 PDLLA의 주사비 치료 | Journal of Cosmetic Derma | 2024 | 증례 연구 (Case ser | 2 |
| 85 | 쥬베룩 | PDLLA 필러가 대식세포와 지방줄기세포를 조절하여 노화 동물 피부의 세포외기질을 증가시킨... | Antioxidants | 2023 | 기초연구 (in vitro  | 0 |
| 86 | 쥬베룩 | 팽창선조(튼살)의 효과적인 개선 방법: 레이저 유도 마이크로젯 주사기와 PDLLA를 이용한... | Journal of Cosmetic Derma | 2024 | 증례 연구 (Case ser | 2 |
| 87 | 쥬베룩 | 눈물고랑 회춘을 위한 PDLLA 주사 후 결절 반응의 에너지 기반 장비 관리 | Journal of Cosmetic Derma | 2024 | 증례보고 (Clinical  | 2 |
| 88 | 쥬베룩 | 쥬베룩의 콜라겐 자극 및 눈물고랑 개선 효능 평가를 위한 초음파 및 방사선학적 패턴: 증례... | Cureus | 2025 | 증례보고 | 2 |
| 89 | 쥬베룩 | 피부과에서의 PDLLA 적용: 문헌 고찰 | Polymers | 2024 | 문헌 고찰 (Literatu | 1 |
| 90 | 쥬비덤 | 쥬비덤 볼벨라의 구순 주위 적용: 12개월 전향적 다기관 공개 연구 | Clinical, Cosmetic and In | 2012 | 전향적 다기관 공개 연구 | 3 |
| 91 | 쥬비덤 | 비순구 장기 교정을 위한 VYC-17.5L(쥬비덤 볼루어)의 안전성과 유효성 | Aesthetic Surgery Journal | 2019 | 전향적 무작위 단맹검 대조  | 4 |
| 92 | 쥬비덤 | 쥬비덤 볼류마(리도카인 포함)의 중안면 볼륨화 효과에 대한 전향적 관찰 연구 | Journal of Cosmetic and L | 2014 | 전향적 관찰 연구 | 3 |
| 93 | 쥬비덤 | VYC-25L(쥬비덤 볼럭스) HA 주사 겔은 하안면 볼륨 복원 및 생성에 장기적으로 안전... | Aesthetic Surgery Journal | 2020 | 전향적 단맹검 무작위 대조  | 4 |
| 94 | 콘셀티나 | 안면 리프팅에서 레이저 절단 vs 성형 폴리디옥사논(PDO) 실의 비교 | Open Science Journal | 2022 | 전향적 비교 연구 | 3 |
| 46 | 클라리티2 | 주사(로사세아) 치료에서 롱펄스 알렉산드라이트+저출력 Nd:YAG 레이저 대 펄스다이 레이... | Lasers in Surgery and Med | 2022 | 무작위 대조 시험 (RCT, | 4 |
| 47 | 클라리티2 | 손발바닥 사마귀(심상성 사마귀) 치료에서 이중파장 롱펄스 755nm 알렉산드라이트/1064... | Journal of Cosmetic and L | 2023 | 전향적 비교 연구 (코호트) | 3 |
| 48 | 클라리티2 | 아시아인 피부의 안면 광노화 치료를 위한 금 나노입자 및 롱펄스 755nm 알렉산드라이트 ... | Lasers in Surgery and Med | 2022 | 전향적 단일군 임상 시험 | 3 |
| 49 | 클라리티2 | 롱펄스 Nd:YAG와 알렉산드라이트 레이저 병합을 이용한 난치성 족저 사마귀의 성공적 치료 | Medical Lasers; Engineeri | 2022 | 증례 보고 (2례) | 2 |
| 50 | 클라리티2 | 주사(로사세아)에서 롱펄스 알렉산드라이트 레이저 치료가 안면 홍조와 피부 미생물 구성에 미... | Photodermatology, Photoim | 2023 | 전향적 다기관 단일군 임상  | 3 |
| 51 | 포텐자 | 고주파(RF) 조사가 멜라노좀 자가포식 증가 및 멜라닌 합성 감소를 통해 자외선B 유도 피... | International Journal of  | 2021 | 기초 연구 (in vitro | 0 |
| 52 | 포텐자 | 모노폴라+바이폴라 고주파 병합 치료가 노화 동물 피부에서 최종당화산물(AGE) 축적 감소를... | International Journal of  | 2022 | 기초 연구 (동물 모델) | 0 |
| 53 | 포텐자 | 고주파(RF) 조사가 ATP 방출 및 CD39 발현 조절을 통해 자외선B 유도 피부 색소침... | International Journal of  | 2023 | 기초 연구 (in vitro | 0 |
| 54 | 포텐자 | 자외선B 유도 피부 염증에서 고주파(RF) 조사가 HMGB1 및 Toll 유사 수용체 활성... | Molecules | 2021 | 기초 연구 (in vitro | 0 |
| 55 | 포텐자 | 고주파(RF) 조사가 주사(로사세아)에서 TRPV1 관련 작열감을 조절함 | Molecules | 2021 | 기초 연구 (in vitro | 0 |
| 56 | 포텐자 | HSP70 상향조절 및 멜라닌 합성 감소를 통한 자외선B 유도 피부 색소침착에 대한 고주파... | Molecules | 2021 | 기초 연구 (in vitro | 0 |
| 57 | 포텐자 | 고주파(RF) 조사가 림프관 신생 증가를 통해 자외선B 유도 피부 색소침착을 완화함 | Molecules | 2022 | 기초 연구 (in vitro | 0 |
| 187 | 플래티넘PTT | 에토좀 금 나노입자를 이용한 광열치료에서 CO2 프랙셔널 레이저 전처치의 효과: 예비 연구 | Journal of Cosmetic Derma | 2025 | Randomized Cont | 4 |
| 188 | 플래티넘PTT | 에토좀 광열치료(ethosome photothermal therapy)란 무엇인가? | Skin Research and Technol | 2024 | Research Letter | 1 |
| 189 | 플래티넘PTT | 에토좀(ETHOSOMEPTT) 광열치료와 Nd:YAG 레이저(Pastelle Pro): 치... | Plastic and Reconstructiv | 2025 | Case Report (Id | 2 |
| 167 | 피코슈어 | 안면 여드름 흉터 치료를 위한 특수 광학 렌즈 장착 피코초 레이저의 사용 | JAMA Dermatology | 2015 | 전향적코호트 | 3 |
| 168 | 피코슈어 | 피코초 알렉산드라이트 레이저와 프랙셔널 렌즈 어레이로 치료한 피부의 조직학적 소견 | Lasers in Surgery and Med | 2016 | 기초연구(in vitro/e | 0 |
| 169 | 피코슈어 | 755nm 알렉산드라이트 피코초 레이저를 이용한 잇몸 색소 치료 | Journal of Cosmetic and L | 2020 | 증례시리즈 | 2 |
| 170 | 피코슈어 | 피코초 알렉산드라이트 레이저를 이용한 문신 치료: 전향적 시험 | Archives of Dermatology | 2012 | 전향적코호트 | 3 |
| 171 | 피코슈어 | 안면 외 부위의 광손상 및 피부결 개선을 위한 회절 렌즈 장착 저에너지 피코초 알렉산드라이... | Journal of Drugs in Derma | 2016 | 전향적코호트 | 3 |
| 172 | 피코슈어 | 가슴 부위 광노화 치료를 위한 특수 렌즈 어레이 장착 피코초 알렉산드라이트 레이저의 안전성... | Lasers in Surgery and Med | 2016 | 전향적코호트 | 3 |
| 173 | 피코슈어 | III~IV형 아시아인 피부의 레이저 반응성 진피 색소 질환에 대한 755nm 피코초 레이... | Dermatologic Surgery | 2020 | 후향적코호트 | 3 |
| 174 | 피코슈어 | 아시아인에서 755nm 피코초 알렉산드라이트 레이저를 이용한 색소 병변 관리의 후향적 분석 | Lasers in Surgery and Med | 2016 | 후향적코호트 | 3 |
| 58 | 피코플러스 | 비후성 반흔(비대 흉터) 치료를 위한 1064nm 피코초 Nd:YAG 레이저의 임상 결과 | Journal of Cosmetic and L | 2018 | 후향적 임상 연구 | 2 |
| 59 | 피코플러스 | 다양한 원인의 외상성 문신에 대한 피코초 Nd:YAG 레이저 치료의 효과와 안전성 | Medical Lasers; Engineeri | 2016 | 증례 시리즈 (9례) | 2 |
| 60 | 피코플러스 | 1064nm 마이크로렌즈 어레이(MLA)형 피코초 레이저 다중 펄스 치료 후 생체내 및 생... | Medical Lasers; Engineeri | 2020 | 기초 연구 (ex vivo  | 0 |
| 61 | 피코플러스 | 피코초 파장변환 595nm Nd:YAG 레이저 치료를 통한 후천성 양측성 오타모반양 반점(... | Medical Lasers; Engineeri | 2016 | 증례 보고 (1례) | 2 |
| 62 | 피코플러스 | 생체외 인체 피부에서 532nm 및 1064nm 마이크로렌즈 어레이형 피코초 레이저 유도 ... | Lasers in Medical Science | 2019 | 기초 연구 (ex vivo) | 0 |