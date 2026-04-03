"""순위 수집 인프라 — API 연동 전 인터페이스 정의.

실제 순위 수집 API(애드로그 등)가 확정되면 이 모듈에 구현.
현재는 인터페이스만 정의하여 향후 연동 준비.
"""

import logging
from datetime import date
from shared.db import get_conn, EQUIPMENT_DB

logger = logging.getLogger(__name__)


class RankCollectorBase:
    """순위 수집기 베이스 클래스."""

    def collect(self, keyword: str, branch_name: str) -> dict | None:
        """키워드+지점으로 실제 네이버 순위 수집.

        Returns:
            {"keyword": str, "rank": int, "source": str} or None
        """
        raise NotImplementedError("API 연동 후 구현 필요")


class PlaceholderCollector(RankCollectorBase):
    """플레이스홀더 — API 미연동 상태."""

    def collect(self, keyword: str, branch_name: str) -> dict | None:
        logger.info(f"[rank_collector] 순위 수집 미구현: {keyword} / {branch_name}")
        return None


def get_rank_comparison(branch_id: int, date_str: str = None) -> dict:
    """구글시트 데이터 vs 실측 순위 비교.

    현재는 시트 데이터만 반환. API 연동 시 실측 데이터 추가.
    """
    if not date_str:
        date_str = date.today().isoformat()

    conn = get_conn(EQUIPMENT_DB)
    try:
        # 시트 기반 데이터
        sheets_data = conn.execute("""
            SELECT date, branch_name, keyword, is_exposed, rank, source
            FROM place_daily
            WHERE branch_id = ? AND date = ?
        """, (branch_id, date_str)).fetchall()

        return {
            "date": date_str,
            "branch_id": branch_id,
            "sheets": [dict(r) for r in sheets_data],
            "actual": [],  # API 연동 후 채워질 영역
            "comparison_available": False,
        }
    finally:
        conn.close()
