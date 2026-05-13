"""
시술 정규화 1단계 진단 산출물 4종 생성 스크립트
생성 대상:
  1-A  category_mapping.md
  1-B  device_info_duplicates.md
  1-C  equipment_unlinked.csv
  1-D  event_to_device_coverage.csv
       event_to_device_unmatched_sample.csv
"""

import sqlite3
import json
import csv
import re
import os
from datetime import datetime
from collections import defaultdict

DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'equipment.db')
OUT_DIR = os.path.dirname(__file__)
TODAY = datetime.now().strftime('%Y-%m-%d')


def normalize_name(s: str) -> str:
    """공백·특수문자 제거 후 소문자 정규화"""
    s = re.sub(r'[\s\-_\(\)（）]', '', s)
    return s.lower()


def parse_aliases(raw) -> list[str]:
    """aliases 컬럼(JSON 문자열 or 빈 문자열) → Python list"""
    if not raw:
        return []
    try:
        result = json.loads(raw)
        if isinstance(result, list):
            return [str(x) for x in result]
        return []
    except Exception:
        return []


def load_data(conn):
    cur = conn.cursor()

    cur.execute('SELECT id, name FROM categories ORDER BY id')
    categories = {r['id']: r['name'] for r in cur.fetchall()}

    cur.execute('SELECT id, name, category, target, summary, aliases, device_type FROM device_info ORDER BY id')
    device_infos = [dict(r) for r in cur.fetchall()]
    for d in device_infos:
        d['aliases_list'] = parse_aliases(d['aliases'])

    cur.execute('''
        SELECT e.id, e.name, e.category_id, c.name as cat_name, e.device_info_id
        FROM equipment e
        LEFT JOIN categories c ON c.id = e.category_id
    ''')
    equipments = [dict(r) for r in cur.fetchall()]

    cur.execute('SELECT raw_event_name, COUNT(*) as cnt FROM evt_items GROUP BY raw_event_name')
    evt_items = {r['raw_event_name']: r['cnt'] for r in cur.fetchall()}

    return categories, device_infos, equipments, evt_items


# ─────────────────────────────────────────────
# 1-A  category_mapping.md
# ─────────────────────────────────────────────

# 매핑 룰: device_info.category → 사용자 8종
# 회색지대 확정 포함
CATEGORY_MAP_RULES = [
    # (device_info.category 패턴, 사용자 카테고리, 근거)
    ('리프팅$', '리프팅', '이름 직접'),
    ('리프팅\\(RF\\)', '리프팅', 'RF 리프팅 장비'),
    ('리프팅\\(실\\)', '리프팅', '실 리프팅'),
    ('리프팅\\(HIFU\\)', '리프팅', 'HIFU 리프팅'),
    ('리프팅/바디', '리프팅', '리프팅+바디 복합'),
    ('RF 마이크로니들', '여드름 흉터', '회색지대 확정: target=흉터/모공/여드름'),
    ('색소$', '색소', '이름 직접'),
    ('레이저\\(색소\\)', '색소', '색소 레이저'),
    ('레이저\\(색소/토닝\\)', '색소', '색소/토닝 레이저'),
    ('레이저\\(색소/재생\\)', '색소', '색소/재생 레이저 → 색소 주 목적'),
    ('레이저\\(색소/혈관\\)', '색소', '색소/혈관 레이저'),
    ('레이저\\(색소/혈관/토닝\\)', '색소', '색소/혈관/토닝'),
    ('레이저\\(색소/혈관/제모\\)', '색소', '색소/혈관/제모'),
    ('레이저\\(색소/피부결\\)', '색소', '색소/피부결'),
    ('레이저\\(제모/색소/혈관\\)', '색소', '제모/색소/혈관'),
    ('레이저\\(제모/색소\\)', '색소', '제모/색소'),
    ('레이저\\(혈관\\)', '색소', '혈관 레이저 → 색소 계열'),
    ('레이저\\(혈관/색소\\)', '색소', '혈관/색소'),
    ('레이저\\(혈관/홍조\\)', '색소', '혈관/홍조'),
    ('레이저\\(재생/홍조\\)', '색소', '재생/홍조'),
    ('주사/부스터', '주사 시술', '주사/부스터 → 주사 시술'),
    ('주사 시술$', '주사 시술', '이름 직접'),
    ('주사 시술\\(필러\\)', '주사 시술', '필러는 주사 시술'),
    ('주사 시술\\(재생\\)', '주사 시술', '재생 주사'),
    ('스킨부스터', '주사 시술', '스킨부스터 = 주사 계열'),
    ('콜라겐 촉진제$', '주사 시술', '회색지대 확정: 필러 포함 주사 시술'),
    ('콜라겐 촉진제\\(필러\\)', '주사 시술', '회색지대 확정: 필러'),
    ('시술기기\\(주입\\)', '주사 시술', '회색지대 확정: 더마샤인 → 주사 시술'),
    ('여드름$', '여드름 치료', '이름 직접'),
    ('여드름/피지', '여드름 치료', '여드름/피지 치료'),
    ('레이저\\(재생/흉터\\)', '여드름 흉터', '회색지대 확정: CO2/프락셀/픽셀'),
    ('레이저\\(CO2/재생\\)', '여드름 흉터', 'CO2 재생 레이저 → 흉터'),
    ('바디$', '비만', '바디 시술 → 비만'),
    ('바디\\(EMS/RF\\)', '비만', '바디 EMS/RF'),
    ('바디\\(HIFU\\)', '비만', '바디 HIFU'),
    ('바디\\(RF\\)', '비만', '바디 RF'),
    ('바디/리프팅\\(EMS\\)', '비만', '바디/리프팅 EMS'),
    ('다이어트', '비만', '다이어트 = 비만'),
    ('제모', '제모', '이름 직접 또는 포함'),
    ('레이저\\(리프팅/제모\\)', '제모', '리프팅/제모 레이저 → 제모 포함'),
    ('관리$', '기타', '일반 관리'),
    ('관리기기$', '기타', '관리기기'),
    ('관리기기\\(RF/LED\\)', '기타', '관리기기'),
    ('관리기기\\(광선\\)', '기타', '관리기기'),
    ('관리기기\\(플라즈마\\)', '기타', '관리기기'),
    ('관리기기\\(필링\\)', '기타', '관리기기'),
    ('관리기기\\(초음파\\)', '기타', '관리기기'),
    ('관리기기/시술', '기타', '관리기기/시술'),
    ('스킨케어/필링', '기타', '스킨케어'),
    ('시술$', '기타', '기타 시술'),
    ('필링$', '기타', '필링 관리'),
    ('모공$', '기타', '모공 관리'),
    ('기타$', '기타', '기타'),
]


def map_category(di_category: str) -> tuple[str, str]:
    """device_info.category → (사용자 8종, 근거). 미매핑 시 ('미분류', '')"""
    for pattern, user_cat, reason in CATEGORY_MAP_RULES:
        if re.search(pattern, di_category):
            return user_cat, reason
    return '미분류', ''


def generate_1a(device_infos, categories):
    from collections import Counter
    # category별 집계
    cat_groups = defaultdict(list)
    for d in device_infos:
        cat_groups[d['category']].append(d)

    lines = []
    lines.append(f'# 카테고리 매핑표')
    lines.append(f'')
    lines.append(f'생성: {TODAY}')
    lines.append(f'')
    lines.append(f'## 사용자 8종 카테고리 (categories 테이블)')
    lines.append(f'1. 리프팅 / 2. 색소 / 3. 주사 시술 / 4. 여드름 치료 / 5. 여드름 흉터 / 6. 비만 / 7. 기타 / 8. 제모')
    lines.append(f'')
    lines.append(f'## device_info.category → 사용자 8종 매핑')
    lines.append(f'')
    lines.append(f'| device_info.category | 건수 | → 사용자 8종 | 근거 |')
    lines.append(f'|---|---|---|---|')

    unmatched = []
    for cat in sorted(cat_groups.keys()):
        cnt = len(cat_groups[cat])
        user_cat, reason = map_category(cat)
        if user_cat == '미분류':
            unmatched.append((cat, cnt))
            lines.append(f'| {cat} | {cnt} | **미분류** | 검수 필요 |')
        else:
            lines.append(f'| {cat} | {cnt} | {user_cat} | {reason} |')

    lines.append(f'')
    lines.append(f'## 회색 지대 확정 사항')
    lines.append(f'- RF 마이크로니들 6건 → 여드름 흉터 (포텐자, 실펌X, 시크릿RF, 버츄RF, 인트라셀, 트리필)')
    lines.append(f'- 레이저(재생/흉터) 3건 → 여드름 흉터 (CO2 레이저, 프락셀, 픽셀)')
    lines.append(f'- 콜라겐 촉진제 4건 → 주사 시술 (올리디아, 스컬트라, 레디어스, 콜라움)')
    lines.append(f'- 시술기기(주입) 1건 → 주사 시술 (더마샤인)')
    lines.append(f'')

    if unmatched:
        lines.append(f'## 매핑 안 된 미분류 (사용자 검수 필요)')
        for cat, cnt in unmatched:
            lines.append(f'- `{cat}` ({cnt}건) — 매핑 룰에 미포함')
    else:
        lines.append(f'## 매핑 안 된 미분류')
        lines.append(f'- 없음 (전체 카테고리 매핑 완료)')

    lines.append(f'')
    lines.append(f'## 사용자 8종별 집계 (매핑 결과)')
    lines.append(f'')
    lines.append(f'| 사용자 카테고리 | device_info 건수 |')
    lines.append(f'|---|---|')
    user_cat_count = Counter()
    for d in device_infos:
        uc, _ = map_category(d['category'])
        user_cat_count[uc] += 1
    for uc in ['리프팅', '색소', '주사 시술', '여드름 치료', '여드름 흉터', '비만', '기타', '제모', '미분류']:
        if user_cat_count[uc]:
            lines.append(f'| {uc} | {user_cat_count[uc]} |')

    return '\n'.join(lines)


# ─────────────────────────────────────────────
# 1-B  device_info_duplicates.md
# ─────────────────────────────────────────────

def generate_1b(device_infos):
    # 유형 1: base name 중복 (공백/숫자/로마자 접미사 제거)
    def base_name(s):
        s = re.sub(r'[\s]', '', s)
        # 숫자 버전 제거: FLX, Pro, Plus, +, 숫자
        s = re.sub(r'(FLX|PRO|PLUS|프로|플러스|\+|\d+)$', '', s, flags=re.IGNORECASE)
        return s.lower()

    base_groups = defaultdict(list)
    for d in device_infos:
        b = base_name(d['name'])
        base_groups[b].append(d)

    type1 = [(b, ds) for b, ds in base_groups.items() if len(ds) > 1]

    # 유형 2: alias cross-reference (다른 row의 name이 어느 row의 aliases에 포함)
    name_to_id = {d['name']: d['id'] for d in device_infos}
    cross_refs = []
    for d in device_infos:
        for alias in d['aliases_list']:
            if alias in name_to_id and name_to_id[alias] != d['id']:
                cross_refs.append({
                    'alias_owner': d,
                    'alias': alias,
                    'matched_id': name_to_id[alias],
                    'matched': next(x for x in device_infos if x['id'] == name_to_id[alias])
                })

    # 유형 3: normalize 후 중복
    norm_groups = defaultdict(list)
    for d in device_infos:
        n = normalize_name(d['name'])
        norm_groups[n].append(d)
    type3 = [(n, ds) for n, ds in norm_groups.items() if len(ds) > 1]

    lines = []
    lines.append(f'# device_info 중복·근접 후보')
    lines.append(f'')
    lines.append(f'생성: {TODAY}')
    lines.append(f'총 device_info: 234건')
    lines.append(f'')
    lines.append(f'## 유형 1: 같은 base name (모델 버전 변형)')
    lines.append(f'')
    if type1:
        for b, ds in sorted(type1, key=lambda x: x[0]):
            ids = ', '.join(f'id={d["id"]} "{d["name"]}"' for d in ds)
            lines.append(f'- [{ds[0]["name"].split("F")[0].split("P")[0][:6]}] {ids}')
            lines.append(f'  - category: {ds[0]["category"]}')
            lines.append(f'  - 권장: 모델 변형이면 alias 통합 (마스터 1개 + alias), 완전 별도 제품이면 유지')
    else:
        lines.append(f'- 검출 없음')

    lines.append(f'')
    lines.append(f'## 유형 2: alias 교차 참조 (다른 row의 name이 alias에 포함)')
    lines.append(f'')
    if cross_refs:
        seen = set()
        for cr in cross_refs:
            key = (cr['alias_owner']['id'], cr['matched_id'])
            if key in seen:
                continue
            seen.add(key)
            lines.append(f'- id={cr["alias_owner"]["id"]} "{cr["alias_owner"]["name"]}"의 alias "{cr["alias"]}"')
            lines.append(f'  → id={cr["matched_id"]} "{cr["matched"]["name"]}" 와 교차')
            lines.append(f'  - 권장: 두 항목 중 하나를 다른 것의 alias로 통합 검토')
    else:
        lines.append(f'- 검출 없음')

    lines.append(f'')
    lines.append(f'## 유형 3: 정규화(공백·특수문자 제거) 후 이름 동일')
    lines.append(f'')
    if type3:
        for n, ds in sorted(type3, key=lambda x: x[0]):
            ids = ', '.join(f'id={d["id"]} "{d["name"]}"' for d in ds)
            lines.append(f'- 정규화="{n}": {ids}')
    else:
        lines.append(f'- 검출 없음')

    lines.append(f'')
    lines.append(f'## 권장 처리 요약')
    total_type1 = sum(len(ds) for _, ds in type1)
    total_type2 = len(set((cr["alias_owner"]["id"], cr["matched_id"]) for cr in cross_refs))
    total_type3 = sum(len(ds) for _, ds in type3)
    lines.append(f'- 유형 1 그룹: {len(type1)}그룹 ({total_type1}건) — 마스터/alias 통합 후보')
    lines.append(f'- 유형 2 교차: {total_type2}쌍 — 통합 또는 alias 재정리 후보')
    lines.append(f'- 유형 3 정규화 중복: {len(type3)}그룹 ({total_type3}건) — 오타/표기 통일 후보')
    lines.append(f'- 위 목록 검수 후 통합 여부를 결정하면 2단계에서 DB 반영')

    return '\n'.join(lines)


# ─────────────────────────────────────────────
# 1-C  equipment_unlinked.csv
# ─────────────────────────────────────────────

def try_match_equipment(eq_name: str, device_infos) -> tuple[str, str | None, str | None]:
    """
    Returns: (suggested_type, suggested_device_info_id, suggested_device_info_name)
    """
    eq_norm = normalize_name(eq_name)

    # 1) 정확 일치
    for d in device_infos:
        if d['name'] == eq_name:
            return 'B_MAP_EXISTING', str(d['id']), d['name']

    # 2) alias 정확 일치
    for d in device_infos:
        if eq_name in d['aliases_list']:
            return 'B_MAP_EXISTING', str(d['id']), d['name']

    # 3) 정규화 후 일치
    for d in device_infos:
        if normalize_name(d['name']) == eq_norm:
            return 'B_MAP_EXISTING', str(d['id']), d['name']

    # 4) alias 정규화 일치
    for d in device_infos:
        for alias in d['aliases_list']:
            if normalize_name(alias) == eq_norm:
                return 'B_MAP_EXISTING', str(d['id']), d['name']

    # 5) 부분 일치 (device_info.name이 equipment.name의 부분문자열 또는 vice versa)
    partial_matches = []
    for d in device_infos:
        d_norm = normalize_name(d['name'])
        if len(d_norm) >= 3 and (d_norm in eq_norm or eq_norm in d_norm):
            partial_matches.append(d)
        else:
            for alias in d['aliases_list']:
                a_norm = normalize_name(alias)
                if len(a_norm) >= 3 and (a_norm in eq_norm or eq_norm in a_norm):
                    partial_matches.append(d)
                    break

    if len(partial_matches) == 1:
        d = partial_matches[0]
        return 'B_MAP_EXISTING', str(d['id']), d['name']
    elif len(partial_matches) > 1:
        # ambiguous — 첫 번째로 추정, C_UNCLEAR로 마크
        d = partial_matches[0]
        return 'C_UNCLEAR', str(d['id']), f'{d["name"]} (복수매칭:{len(partial_matches)})'

    return 'A_NEW_MASTER', '', ''


def generate_1c(equipments, device_infos, categories):
    # 미연결만 필터
    unlinked = [e for e in equipments if e['device_info_id'] is None]

    # 이름+카테고리별 집계
    groups = defaultdict(lambda: {'count': 0, 'category_id': None, 'cat_name': None})
    for e in unlinked:
        key = (e['name'], e['category_id'])
        groups[key]['count'] += 1
        groups[key]['category_id'] = e['category_id']
        groups[key]['cat_name'] = e.get('cat_name') or ''

    rows = []
    for (name, cat_id), info in groups.items():
        stype, sdi_id, sdi_name = try_match_equipment(name, device_infos)
        notes = ''
        if stype == 'A_NEW_MASTER':
            notes = 'device_info에 마스터 없음. 신규 등록 권장'
        elif stype == 'B_MAP_EXISTING':
            notes = f'device_info id={sdi_id} "{sdi_name}" 에 매핑 룰 보강 또는 alias 추가'
        elif stype == 'C_UNCLEAR':
            notes = f'복수 매칭 — 사용자 검수 필요. 후보: {sdi_name}'

        rows.append({
            'name': name,
            'total_count': info['count'],
            'category_id': cat_id or '',
            'category_name': info['cat_name'],
            'suggested_type': stype,
            'suggested_device_info_id': sdi_id,
            'suggested_device_info_name': sdi_name if stype != 'C_UNCLEAR' else (sdi_name.split(' (')[0] if sdi_name else ''),
            'notes': notes,
        })

    rows.sort(key=lambda r: (-r['total_count'], r['name']))

    return rows


# ─────────────────────────────────────────────
# 1-D  event_to_device_coverage.csv
# ─────────────────────────────────────────────

def try_match_event(raw_name: str, device_infos) -> tuple[str, list]:
    """
    Returns: (match_status, matched_device_infos)
    match_status: exact_name_match / alias_match / partial_match / ambiguous / no_match
    """
    raw_norm = normalize_name(raw_name)

    # 1) 완전 일치: raw_event_name == device_info.name
    exact = [d for d in device_infos if d['name'] == raw_name]
    if exact:
        return 'exact_name_match', exact

    # 2) alias 완전 일치
    alias_exact = [d for d in device_infos if raw_name in d['aliases_list']]
    if alias_exact:
        return 'alias_match', alias_exact

    # 3) alias 부분 포함 (alias가 raw_name의 substring, 최소 3자)
    alias_partial = []
    for d in device_infos:
        for alias in d['aliases_list']:
            a_norm = normalize_name(alias)
            if len(a_norm) >= 3 and a_norm in raw_norm:
                alias_partial.append(d)
                break
    if len(alias_partial) == 1:
        return 'alias_match', alias_partial
    elif len(alias_partial) > 1:
        return 'ambiguous', alias_partial

    # 4) device_info.name이 raw_name의 substring (정규화 기준, 최소 3자)
    partial = []
    for d in device_infos:
        d_norm = normalize_name(d['name'])
        if len(d_norm) >= 3 and d_norm in raw_norm:
            partial.append(d)

    if len(partial) == 1:
        return 'partial_match', partial
    elif len(partial) > 1:
        return 'ambiguous', partial

    return 'no_match', []


EPILATION_PATTERNS = ['男)', '女)', '겨드랑이', '브라질리언', '비키니', '팔 전체',
                      '허벅지', '다리 전체', '가슴', '아래턱', '등 전체', '엉덩이',
                      '종아리', '팔 하완', '팔 상완', '발 ', '이마', '뒷목', '앞목',
                      '미간', '눈썹', '유륜', '배레', '얼굴전체', '뒤통수', '팔꿈치',
                      '무릎', '겨드랑', '허리', '남성', '여성']


def is_epilation(name: str) -> bool:
    return any(p in name for p in EPILATION_PATTERNS)


def generate_1d(evt_items, device_infos):
    results = defaultdict(lambda: {'count': 0, 'samples': []})

    for raw_name, cnt in evt_items.items():
        status, matched = try_match_event(raw_name, device_infos)
        results[status]['count'] += cnt
        results[status]['samples'].append((raw_name, cnt))

    # 커버리지 CSV
    coverage_rows = []
    for status in ['exact_name_match', 'alias_match', 'partial_match', 'ambiguous', 'no_match']:
        info = results[status]
        # 샘플 상위 5개 (count 기준)
        samples_sorted = sorted(info['samples'], key=lambda x: -x[1])[:5]
        sample_str = ' | '.join(s[0] for s in samples_sorted)
        coverage_rows.append({
            'match_status': status,
            'count_items': info['count'],
            'count_unique_names': len(info['samples']),
            'sample_raw_event_names': sample_str,
        })

    # unmatched sample CSV (no_match + ambiguous 상위 200)
    unmatched_candidates = results['no_match']['samples'] + results['ambiguous']['samples']
    # 제모 부위 이름 판별 추가
    unmatched_top = sorted(unmatched_candidates, key=lambda x: -x[1])[:200]
    unmatched_rows = [
        {'raw_event_name': name, 'count': cnt,
         'is_epilation': 'Y' if is_epilation(name) else 'N'}
        for name, cnt in unmatched_top
    ]

    return coverage_rows, unmatched_rows


# ─────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────

def main():
    print(f'DB: {os.path.abspath(DB_PATH)}')
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    categories, device_infos, equipments, evt_items = load_data(conn)

    os.makedirs(OUT_DIR, exist_ok=True)

    # 1-A
    print('생성 중: 1-A category_mapping.md ...')
    content_1a = generate_1a(device_infos, categories)
    with open(os.path.join(OUT_DIR, 'category_mapping.md'), 'w', encoding='utf-8') as f:
        f.write(content_1a)
    print('  완료')

    # 1-B
    print('생성 중: 1-B device_info_duplicates.md ...')
    content_1b = generate_1b(device_infos)
    with open(os.path.join(OUT_DIR, 'device_info_duplicates.md'), 'w', encoding='utf-8') as f:
        f.write(content_1b)
    print('  완료')

    # 1-C
    print('생성 중: 1-C equipment_unlinked.csv ...')
    rows_1c = generate_1c(equipments, device_infos, categories)
    with open(os.path.join(OUT_DIR, 'equipment_unlinked.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'name', 'total_count', 'category_id', 'category_name',
            'suggested_type', 'suggested_device_info_id', 'suggested_device_info_name', 'notes'
        ])
        writer.writeheader()
        writer.writerows(rows_1c)
    # 통계
    type_counts = defaultdict(int)
    for r in rows_1c:
        type_counts[r['suggested_type']] += r['total_count']
    total_unlinked = sum(r['total_count'] for r in rows_1c)
    print(f'  완료: 총 {total_unlinked}건 ({len(rows_1c)} 이름그룹)')
    for t, c in sorted(type_counts.items()):
        print(f'    {t}: {c}건')

    # 1-D
    print('생성 중: 1-D event_to_device_coverage.csv ...')
    coverage_rows, unmatched_top = generate_1d(evt_items, device_infos)
    with open(os.path.join(OUT_DIR, 'event_to_device_coverage.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'match_status', 'count_items', 'count_unique_names', 'sample_raw_event_names'
        ])
        writer.writeheader()
        writer.writerows(coverage_rows)

    with open(os.path.join(OUT_DIR, 'event_to_device_unmatched_sample.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['raw_event_name', 'count', 'is_epilation'])
        writer.writeheader()
        writer.writerows(unmatched_top)

    # 커버리지 통계 출력
    total_items = sum(r['count_items'] for r in coverage_rows)
    matched_items = sum(r['count_items'] for r in coverage_rows if r['match_status'] not in ('no_match', 'ambiguous'))
    print(f'  완료: 총 {total_items}건, 매칭 성공 {matched_items}건 ({matched_items/total_items*100:.1f}%)')
    for r in coverage_rows:
        print(f'    {r["match_status"]}: {r["count_items"]}건 ({r["count_unique_names"]} 고유명)')

    print()
    print('=== 산출물 생성 완료 ===')
    for fname in ['category_mapping.md', 'device_info_duplicates.md',
                  'equipment_unlinked.csv', 'event_to_device_coverage.csv',
                  'event_to_device_unmatched_sample.csv']:
        path = os.path.join(OUT_DIR, fname)
        size = os.path.getsize(path)
        print(f'  {fname} ({size:,} bytes)')


if __name__ == '__main__':
    main()
