#!/usr/bin/env python3
"""180건 논문에 대해 easy_summary(쉬운 요약)를 일괄 생성하여 DB에 UPDATE"""
import sqlite3, sys, json

sys.stdout.reconfigure(encoding='utf-8')
DB = 'data/equipment.db'

STRENGTH = {
    5: '★★★ 강한 근거(메타분석/체계적 고찰)',
    4: '★★★ 강한 근거(RCT)',
    3: '★★☆ 중간 근거(코호트/비교연구)',
    2: '★☆☆ 참고 수준(증례보고)',
    1: '★☆☆ 전문가 의견/리뷰',
    0: '☆☆☆ 기초연구/전임상',
}

CLAIM_VERB = {
    5: '입증',
    4: '입증',
    3: '확인',
    2: '보고',
    1: '제시',
    0: '규명',
}


def build_easy_summary(row):
    """papers 행 데이터로부터 easy_summary 문자열을 생성"""
    pid, device, ev, stype, conclusion, stats_raw, title_ko, journal, year, sample = row

    # 근거 강도
    strength = STRENGTH.get(ev, '☆☆☆ 기초연구')
    verb = CLAIM_VERB.get(ev, '확인')

    # quotable_stats 파싱
    try:
        stats = json.loads(stats_raw) if stats_raw else []
    except (json.JSONDecodeError, TypeError):
        stats = []

    # 핵심 수치 (최대 2개)
    stat_lines = []
    for s in stats[:2]:
        stat_lines.append(f'  - {s}')

    # 결론에서 첫 문장 추출 (마침표 기준)
    conclusion_first = ''
    if conclusion:
        sentences = conclusion.split('.')
        if sentences:
            conclusion_first = sentences[0].strip()
            if not conclusion_first.endswith('.'):
                conclusion_first += '.'

    # 장비명 처리
    device_name = device or '해당 시술'

    # 활용 문장 생성
    if ev >= 4:
        usage = f'"{device_name}는 {stype or "임상연구"}에서 효과가 {verb}된 시술입니다 ({journal}, {year})"'
    elif ev == 3:
        usage = f'"{device_name}의 효과가 임상에서 {verb}되었습니다 ({journal}, {year})"'
    elif ev == 2:
        usage = f'"{device_name}를 이용한 치료 사례가 {verb}되었습니다 ({journal}, {year})"'
    elif ev == 1:
        usage = f'"전문가들은 {device_name}의 효과 가능성을 {verb}하고 있습니다 ({journal}, {year})"'
    else:
        usage = f'"기초연구에서 {device_name}의 작용 메커니즘이 {verb}되었습니다 ({journal}, {year})"'

    # 조립
    lines = [f'[{strength}] {stype or "연구"}']
    if conclusion_first:
        lines.append(f'핵심: {conclusion_first}')
    if stat_lines:
        lines.append('주요 수치:')
        lines.extend(stat_lines)
    if sample:
        lines.append(f'대상: {sample}')
    lines.append(f'활용: {usage}')

    return '\n'.join(lines)


def main():
    conn = sqlite3.connect(DB)
    conn.execute('PRAGMA journal_mode=WAL')
    cur = conn.cursor()

    cur.execute('''
        SELECT p.id, d.name, p.evidence_level, p.study_type, p.conclusion,
               p.quotable_stats, p.title_ko, p.journal, p.pub_year, p.sample_size
        FROM papers p
        LEFT JOIN device_info d ON p.device_info_id = d.id
        ORDER BY p.id
    ''')
    rows = cur.fetchall()

    updated = 0
    for row in rows:
        pid = row[0]
        summary = build_easy_summary(row)
        cur.execute('UPDATE papers SET easy_summary = ?, updated_at = datetime("now") WHERE id = ?',
                    (summary, pid))
        updated += 1

    conn.commit()
    print(f'easy_summary 생성 완료: {updated}건 UPDATE')

    # 샘플 출력
    for sample_id in [161, 63, 51, 175]:
        cur.execute('SELECT id, easy_summary FROM papers WHERE id = ?', (sample_id,))
        r = cur.fetchone()
        if r:
            print(f'\n--- #{r[0]} ---')
            print(r[1])

    conn.close()


if __name__ == '__main__':
    main()
