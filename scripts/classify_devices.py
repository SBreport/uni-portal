"""장비 타입 분류 스크립트.

device_info.device_type 컬럼 추가 후
category 기반으로 자동 분류:
  - 'injection': 주사/시술/필러/재생/콜라겐촉진제/스킨부스터
  - 'care': 관리/관리기기/스킨케어/필링
  - 'material': 기타 중 스티머/확대경/인바디 등 소모품·보조기기
  - 'equipment': 그 외 (레이저, 리프팅, 바디, 등)
"""

import sqlite3
import sys
import os

# 프로젝트 루트를 경로에 추가
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from shared.db import get_conn, EQUIPMENT_DB

INJECTION_CATEGORIES = {
    '주사/부스터',
    '주사 시술',
    '주사 시술(필러)',
    '주사 시술(재생)',
    '콜라겐 촉진제',
    '콜라겐 촉진제(필러)',
    '스킨부스터',
    '주사/인젝터',
}

CARE_CATEGORIES = {
    '관리',
    '관리기기',
    '관리기기/시술',
    '관리기기(초음파)',
    '관리기기(RF/LED)',
    '관리기기(광선)',
    '관리기기(플라즈마)',
    '관리기기(필링)',
    '스킨케어/필링',
    '필링',
    '시술',
    '시술기기(주입)',
    'RF 마이크로니들',
}

# 기타 카테고리 중 material로 분류할 이름 키워드
MATERIAL_NAMES = {'스티머', '확대경', '인바디'}


def get_device_type(category: str, name: str) -> str:
    if category in INJECTION_CATEGORIES:
        return 'injection'
    if category in CARE_CATEGORIES:
        return 'care'
    if category == '기타':
        for kw in MATERIAL_NAMES:
            if kw in name:
                return 'material'
    return 'equipment'


def main():
    conn = get_conn(EQUIPMENT_DB)
    try:
        # 1) device_type 컬럼 추가 (idempotent)
        try:
            conn.execute(
                "ALTER TABLE device_info ADD COLUMN device_type TEXT DEFAULT 'equipment'"
            )
            conn.commit()
            print("[classify_devices] device_type 컬럼 추가 완료")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print("[classify_devices] device_type 컬럼 이미 존재 — 스킵")
            else:
                raise

        # 2) 전체 분류 실행
        rows = conn.execute(
            "SELECT id, name, category FROM device_info"
        ).fetchall()

        counts = {'equipment': 0, 'injection': 0, 'care': 0, 'material': 0}
        for r in rows:
            dtype = get_device_type(r['category'] or '', r['name'] or '')
            conn.execute(
                "UPDATE device_info SET device_type = ? WHERE id = ?",
                (dtype, r['id']),
            )
            counts[dtype] += 1

        conn.commit()
        total = sum(counts.values())
        print(f"[classify_devices] 분류 완료: 총 {total}건")
        for k, v in counts.items():
            print(f"  {k}: {v}건")

    finally:
        conn.close()


if __name__ == '__main__':
    main()
