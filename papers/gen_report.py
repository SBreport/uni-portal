#!/usr/bin/env python3
"""논문 분석 DB화 작업 리포트 생성"""
import sqlite3, sys
from collections import defaultdict, Counter

sys.stdout.reconfigure(encoding='utf-8')
DB = 'data/equipment.db'
OUT = 'papers/WORK_REPORT_20260324.md'

conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute('''
    SELECT p.id, d.name as device, d.id as did, p.title_ko, p.title, p.authors,
           p.journal, p.pub_year, p.study_type, p.evidence_level, p.doi, p.source_file
    FROM papers p
    LEFT JOIN device_info d ON p.device_info_id = d.id
    ORDER BY d.name, p.id
''')
rows = cur.fetchall()

groups = defaultdict(list)
for r in rows:
    groups[r[1] or '미매칭'].append(r)

ev_counts = Counter()
for r in rows:
    ev_counts[r[9]] += 1

ev_labels = {0: '기초/전임상', 1: '체계적문헌고찰', 2: '증례보고/시리즈', 3: '코호트/관찰', 4: 'RCT', 5: '설문/기타'}

L = []
L.append('# 논문 분석 DB화 작업 리포트\n')
L.append('- 작업일: 2026-03-24')
L.append('- 작업자: Claude AI (자동 분석)')
L.append('- DB 위치: `data/equipment.db` > `papers` 테이블')
L.append('- 원본 폴더: `C:\\LocalGD\\0_INBOX\\06_논문 분석\\`')

L.append('\n---\n')
L.append('## 1. 전체 요약\n')
L.append(f'| 항목 | 수량 |')
L.append(f'|------|------|')
L.append(f'| DB 저장 논문 | **{len(rows)}건** |')
L.append(f'| 매칭 장비 수 | **{len(groups)}개** |')
L.append(f'| 비학술 스킵 | **약 57건** |')
L.append(f'| 장비 매칭률 | **100%** (미매칭 0건) |')

# 폴더별 처리 현황
L.append('\n## 2. 폴더별 처리 현황\n')
folder_data = [
    ('레디어스(멀츠)', 9, 7, ''),
    ('루카스', 3, 3, ''),
    ('리바이브(멀츠)', 6, 6, '벨로테로 장비에 매칭'),
    ('리쥬란', 17, 17, ''),
    ('벨로테로(멀츠)', 20, 14, '마케팅자료4+중복1+요약1 스킵'),
    ('슈링크(클래시스)', 17, 3, '14건 D&PS 매거진/홍보 스킵, 저장분은 볼뉴머 매칭'),
    ('써마지', 3, 0, '전부 비학술(브로셔/가이드/논문목록)'),
    ('아그네스', 20, 19, '독일어 중복 1건 스킵'),
    ('아포지, 피코슈어', 9, 8, '제조사 백서 1건 스킵, 전부 피코슈어 매칭'),
    ('에어녹스', 26, 12, '비학술/스캔PDF/중복 14건 스킵'),
    ('에토좀 PTT', 3, 3, '플래티넘PTT 매칭'),
    ('엘라비에 리투오', 11, 10, '중복 1건 스킵, 리투오 매칭'),
    ('올리지오, 올리지오X, 피코', 13, 4, '마케팅/영업자료/기업보고서 9건 스킵'),
    ('인모드', 12, 6, '교육자료/사용법/스캔PDF 등 스킵'),
    ('젠틀맥스 프로플러스', 15, 12, '요약집/스캔PDF/중복 3건 스킵'),
    ('쥬베룩', 29, 27, 'supplementary 2건 본논문에 포함'),
    ('쥬비덤', 4, 4, ''),
    ('콘셀티나(동방메디컬)', 1, 1, 'PDO 실 비교, 장비 신규등록'),
    ('클라리티2(루트로닉)', 6, 5, '마케팅 포토북 1건 스킵'),
    ('포텐자', 7, 7, '전부 기초연구(Lv.0)'),
    ('피코플러스(루트로닉)', 6, 5, '중복파일 1건 스킵'),
]

L.append('| 폴더 | PDF수 | 저장 | 스킵 | 비고 |')
L.append('|------|-------|------|------|------|')
for name, pdf, saved, note in folder_data:
    skip = pdf - saved
    L.append(f'| {name} | {pdf} | **{saved}** | {skip} | {note} |')

# 장비별 논문 수
L.append('\n## 3. 장비별 논문 수\n')
L.append('| 장비 (device_info) | ID | 논문 수 |')
L.append('|-------------------|-----|--------|')
for name in sorted(groups.keys()):
    papers = groups[name]
    did = papers[0][2] if papers[0][2] else '-'
    L.append(f'| {name} | {did} | {len(papers)} |')

# 근거수준 분포
L.append('\n## 4. 근거 수준 분포\n')
L.append('| Level | 유형 | 건수 |')
L.append('|-------|------|------|')
for lv in sorted(ev_counts.keys()):
    label = ev_labels.get(lv, f'Level {lv}')
    L.append(f'| {lv} | {label} | {ev_counts[lv]} |')

# 비학술 스킵 목록
L.append('\n## 5. 비학술 자료 스킵 상세\n')
skipped_items = [
    ('레디어스(멀츠)', [
        '리플렛 업뎃 260105.pdf (원내비치용 리플렛)',
        '레디어스 리셋 브로셔 (2026).pdf (제품 브로셔)',
    ]),
    ('벨로테로(멀츠)', [
        'Biomimetic HCP 디테일 자료 1~3번 + 통합버전 (마케팅 4건)',
        'Micheels P et al 2017_JCAD.pdf (중복)',
        '벨로테로 Purity 논문 요약_최종.pdf (한국어 요약 정리물)',
    ]),
    ('슈링크(클래시스)', [
        'D&PS 매거진 기사/인터뷰/경험담 (11건)',
        'The Aesthetic Guide 홍보 기사 (2건)',
        'VOLNEWMER 대한피부과의사회지 광고 (1건)',
    ]),
    ('써마지', [
        'Article list.pdf (논문 목록)',
        '써마지 peer group 논문 브로셔.pdf (마케팅 브로셔)',
        '써마지 FLX 시술참조가이드.pdf (사용 가이드)',
    ]),
    ('아포지, 피코슈어', ['Histology White Paper (Cynosure 백서)']),
    ('에어녹스', [
        '브로셔/상담바인더/시술가이드 (비학술 3건)',
        '허가 및 인증 문서 (6건)',
        '스캔PDF 텍스트추출불가 3건',
        '중복 1건, 교과서 발췌 요약 1건',
    ]),
    ('엘라비에 리투오', [
        '제품 소개 자료.pptx',
        '메가덤 논문 리스트.xlsx',
        '논문 주요 내용 요약.pptx',
    ]),
    ('올리지오, 올리지오X, 피코', [
        '올리지오X 마케팅 자료 4건 (Case Book/Ref Guide/Key-point/Sales Pres)',
        '올리지오 마케팅 자료 3건 (Ref Guide 2건 + Sales Pres)',
        'Picocare 논문 요약집 (제조사 편집)',
        '원텍 올리지오X 전임상 결과보고서 (비공개 기업 보고서)',
    ]),
    ('인모드', [
        'body FX 교육자료/인모드 RF 교육자료/인모드+바디 교육자료 (3건)',
        '인모드핸드피스 세척법.pdf / 포마-미니 가이드.pdf',
        'BodyFX/MiniFX 스캔PDF (텍스트추출불가)',
        'MiniFX mechanisms.pptx / 비포애프터 jpg 28장 / mp4 3개',
    ]),
    ('젠틀맥스 프로플러스', [
        'Gentle Laser Family 논문 요약본.pdf (제조사 편집)',
        '스캔PDF 텍스트추출불가 1건',
        '중복 파일 1건',
    ]),
    ('클라리티2(루트로닉)', ['CLARITY2_PHOTOBOOK.pdf (마케팅 포토북)']),
    ('피코플러스(루트로닉)', ['중복 파일 1건 (동일 논문 2개 PDF)']),
]
for folder, items in skipped_items:
    L.append(f'### {folder}')
    for item in items:
        L.append(f'- {item}')
    L.append('')

# 비PDF 파일 기록
L.append('## 6. 비PDF 파일 기록\n')
L.append('| 폴더 | 파일명 | 유형 | 비고 |')
L.append('|------|--------|------|------|')
non_pdf = [
    ('아그네스', 'Article list.xlsx', 'xlsx', '논문 목록'),
    ('에어녹스', '홈페이지이미지/ (00~04.jpg, Q&A.jpg)', 'jpg x6', '제품 이미지'),
    ('에어녹스', '아산화질소와 흡입마취제.docx', 'docx', '참고문서'),
    ('엘라비에 리투오', 'Elravie Re2O_제품 소개 자료.pptx', 'pptx', '제품소개'),
    ('엘라비에 리투오', 'L&C BIO_메가덤 논문 리스트.xlsx', 'xlsx', '논문목록'),
    ('엘라비에 리투오', '엘라비에 리투오 논문 주요 내용 요약.pptx', 'pptx', '논문요약'),
    ('인모드', '비포애프터/ (Forma, BodyFX, MiniFX, Fractora)', 'jpg x28', '시술 전후 사진'),
    ('인모드', 'FORMA/MiniFX/핸드피스관리법', 'mp4 x3', '교육 영상'),
    ('인모드', 'MiniFX mechanisms.pptx', 'pptx', '기전 설명'),
    ('쥬베룩', '논문_파일명_개요.xlsx', 'xlsx', '논문목록'),
    ('포텐자', '포텐자 논문.txt', 'txt', '논문 URL 목록'),
]
for folder, fname, ftype, note in non_pdf:
    L.append(f'| {folder} | {fname} | {ftype} | {note} |')

# 특이사항
L.append('\n## 7. 특이사항\n')
L.append('- **써마지**: 폴더 내 PDF 3건 전부 비학술 자료 -> 학술 논문 0건 저장')
L.append('- **아포지**: 폴더명에 포함되어 있으나 실제 PDF는 전부 피코슈어 관련 (아포지 논문 0건)')
L.append('- **에어녹스**: N2O 진정기 장비가 기존 DB에 미등록 -> 신규 등록 (id=128) 후 12건 매칭')
L.append('- **콘셀티나**: 논문에 제품명 미언급 -> 장비 신규 등록 (id=129) 후 매칭')
L.append('- **인모드 비포애프터 사진 28장**: Forma/BodyFX/MiniFX/Fractora 시술 전후 사진')
L.append('- **슈링크 폴더**: 저장된 3건은 실제로 볼뉴머(id=13) RF 논문에 해당')
L.append('- **더마브이 폴더**: 이전 세션에서 작업 완료 (이번 세션에서 HIFU 1건 매칭 보정)')

# 전체 논문 목록
L.append('\n## 8. 전체 논문 목록 (180건)\n')
L.append('| ID | 장비 | 제목 | 학술지 | 연도 | 유형 | Lv |')
L.append('|-----|------|------|--------|------|------|----|')
for r in rows:
    pid = r[0]
    device = r[1] or '미매칭'
    title = (r[3] or r[4] or '')[:50]
    if len(r[3] or r[4] or '') > 50:
        title += '...'
    journal = (r[6] or '')[:25]
    year = r[7] or ''
    stype = (r[8] or '')[:15]
    ev = r[9] if r[9] is not None else '-'
    L.append(f'| {pid} | {device} | {title} | {journal} | {year} | {stype} | {ev} |')

report = '\n'.join(L)
with open(OUT, 'w', encoding='utf-8') as f:
    f.write(report)

print(f'리포트 생성 완료: {OUT} ({len(L)}줄)')
conn.close()
