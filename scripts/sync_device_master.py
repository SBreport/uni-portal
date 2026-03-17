"""
data/device_master.json → device_info 테이블 동기화 스크립트

사용법:
    python scripts/sync_device_master.py              # 전체 동기화
    python scripts/sync_device_master.py --verified    # is_verified=true 항목만
    python scripts/sync_device_master.py --dry-run     # 실제 반영 없이 미리보기
"""

import json
import os
import sys
import argparse

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from equipment.db import upsert_device_info, get_all_device_info

MASTER_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "device_master.json"
)


def load_master():
    with open(MASTER_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("devices", [])


def sync(only_verified=False, dry_run=False):
    devices = load_master()
    existing = {d["name"]: d for d in get_all_device_info()}

    added, updated, skipped = 0, 0, 0

    for dev in devices:
        name = dev["name"]

        if only_verified and not dev.get("is_verified", False):
            skipped += 1
            continue

        aliases_str = ", ".join(dev.get("aliases", []))
        is_verified = 1 if dev.get("is_verified", False) else 0

        action = "UPDATE" if name in existing else "ADD"

        if dry_run:
            print(f"  [DRY-RUN] {action}: {name} (category={dev.get('category', '')}, verified={is_verified})")
        else:
            upsert_device_info(
                name=name,
                category=dev.get("category", ""),
                summary=dev.get("summary", ""),
                target=dev.get("target", ""),
                mechanism=dev.get("mechanism", ""),
                note=dev.get("note", ""),
                aliases=aliases_str,
                is_verified=is_verified,
            )

        if action == "ADD":
            added += 1
        else:
            updated += 1

    print(f"\n동기화 완료: 추가 {added}건, 수정 {updated}건, 스킵 {skipped}건")
    if dry_run:
        print("(dry-run 모드 - 실제 DB에는 반영되지 않았습니다)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="device_master.json → DB 동기화")
    parser.add_argument("--verified", action="store_true", help="검증된 항목만 동기화")
    parser.add_argument("--dry-run", action="store_true", help="실제 반영 없이 미리보기")
    args = parser.parse_args()

    if not os.path.exists(MASTER_PATH):
        print(f"ERROR: {MASTER_PATH} 파일을 찾을 수 없습니다.")
        sys.exit(1)

    print(f"소스: {MASTER_PATH}")
    print(f"옵션: verified_only={args.verified}, dry_run={args.dry_run}")
    print("-" * 50)

    sync(only_verified=args.verified, dry_run=args.dry_run)
