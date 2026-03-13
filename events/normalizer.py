"""카테고리 정규화 및 시술명 매핑 모듈.

지점마다 다른 카테고리명을 표준 카테고리로 매핑하고,
패키지 구성요소에서 시술명을 추출한다.
"""

import json
import os
import re
from pathlib import Path

# normalization 파일 경로
_NORM_DIR = Path(os.path.dirname(__file__)).parent / "normalization"
CATEGORY_MAP_FILE = _NORM_DIR / "category_map.json"
TREATMENT_PATTERNS_FILE = _NORM_DIR / "treatment_patterns.json"
REVIEW_QUEUE_FILE = _NORM_DIR / "review_queue.json"


def load_json(path: Path) -> dict:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class CategoryNormalizer:
    """카테고리 별명을 표준 카테고리로 매핑."""

    def __init__(self):
        config = load_json(CATEGORY_MAP_FILE)
        self.mappings: dict[str, str] = config.get("mappings", {})
        self._unmapped: list[str] = []

    def normalize(self, raw_category: str) -> str:
        """원시 카테고리명 → 표준 카테고리명."""
        cleaned = raw_category.strip()

        # 1. 정확한 매핑
        if cleaned in self.mappings:
            return self.mappings[cleaned]

        # 2. 정규화된 형태로 매핑
        normalized = re.sub(r"\s+", "", cleaned)
        for alias, standard in self.mappings.items():
            if re.sub(r"\s+", "", alias) == normalized:
                return standard

        # 3. 부분 일치 (길이 3자 이상)
        best_match = None
        best_len = 0
        for alias, standard in self.mappings.items():
            if len(alias) < 3:
                continue
            if alias in cleaned and len(alias) > best_len:
                best_match = standard
                best_len = len(alias)
        if best_match:
            return best_match

        # 4. 미매핑 → '기타'
        if cleaned not in self._unmapped:
            self._unmapped.append(cleaned)
        return "기타"

    def get_unmapped(self) -> list[str]:
        return self._unmapped

    def save_review_queue(self) -> None:
        """매핑되지 않은 카테고리를 리뷰 큐 파일에 저장."""
        if not self._unmapped:
            return
        existing = load_json(REVIEW_QUEUE_FILE)
        queue = existing.get("unmapped_categories", [])
        for item in self._unmapped:
            if item not in queue:
                queue.append(item)
        existing["unmapped_categories"] = queue
        save_json(REVIEW_QUEUE_FILE, existing)


class ComponentParser:
    """패키지 구성요소에서 시술명, 용량, 회차를 추출."""

    def __init__(self):
        config = load_json(TREATMENT_PATTERNS_FILE)
        self.known_brands: list[str] = config.get("known_brands", [])
        self.dosage_pattern = re.compile(
            config.get("dosage_pattern", r"(\d+(?:\.\d+)?)\s*(cc|ml|mg|vial|샷|유닛|줄)"),
            re.IGNORECASE,
        )
        self.session_pattern = re.compile(
            config.get("session_pattern", r"(\d+)\s*회")
        )

    def parse_component(self, text: str) -> dict:
        """구성요소 텍스트에서 구조화된 정보 추출."""
        result = {
            "raw": text.strip(),
            "treatment_name": text.strip(),
            "dosage": None,
            "session_count": None,
            "brand": None,
        }

        dosage_match = self.dosage_pattern.search(text)
        if dosage_match:
            result["dosage"] = dosage_match.group(0)

        session_match = self.session_pattern.search(text)
        if session_match:
            result["session_count"] = int(session_match.group(1))

        for brand in self.known_brands:
            if brand in text:
                result["brand"] = brand
                break

        name = text.strip()
        name = self.dosage_pattern.sub("", name)
        name = self.session_pattern.sub("", name)
        name = re.sub(r"\s+", " ", name).strip()
        if name:
            result["treatment_name"] = name

        return result
