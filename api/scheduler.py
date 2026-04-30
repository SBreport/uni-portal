"""백그라운드 스케줄러 — APScheduler 기반.

- 블로그 노션 동기화: 매일 06:00 KST
- 블로그 제목 스크래핑 (06:00 직후)
- 플레이스 오늘 동기화: 매일 10:30, 18:30 KST (2회)
- 웹페이지 오늘 동기화: 매일 11:00, 19:00 KST (2회)
- 플레이스/웹페이지 일별 스냅샷: 매일 23:00 KST
- SB체커 자동 측정: 매일 20:00 KST
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger("scheduler")

scheduler = AsyncIOScheduler(timezone="Asia/Seoul")


async def _run_blog_sync():
    """노션 → DB 블로그 동기화 + 제목 스크래핑 (매일 06:00)."""
    logger.info("[scheduler] 블로그 동기화 시작")
    try:
        from blog.sync_notion import incremental_sync, NOTION_BLOG_DB_ID
        from blog.post_queries import get_notion_token

        token = get_notion_token()
        db_id = NOTION_BLOG_DB_ID
        if not token or not db_id:
            logger.warning("[scheduler] 노션 토큰/DB ID 미설정 — 동기화 건너뜀")
            return

        result = incremental_sync(token, db_id, triggered_by="auto")
        logger.info(f"[scheduler] 블로그 동기화 완료: {result}")
    except Exception as e:
        logger.error(f"[scheduler] 블로그 동기화 실패: {e}", exc_info=True)
        return  # 노션 동기화 실패 시 제목 스크래핑도 의미 없음

    # 노션 동기화 직후 — 새 글의 빈 제목을 스크래핑으로 보충
    try:
        import asyncio
        from blog.scrape_titles import scrape_missing_titles
        scrape_result = await asyncio.to_thread(scrape_missing_titles, 50, 0.2)
        logger.info(f"[scheduler] 블로그 제목 스크래핑: {scrape_result}")
    except Exception as e:
        logger.error(f"[scheduler] 블로그 제목 스크래핑 실패: {e}", exc_info=True)


async def _run_place_today_sync():
    """플레이스 오늘 동기화 (매일 18:30 KST)."""
    logger.info("[scheduler] 플레이스 오늘 동기화 시작 (auto)")
    try:
        import asyncio
        from place.sync_to_db import sync_all_to_db
        # AsyncIO loop 블로킹 방지
        result = await asyncio.to_thread(sync_all_to_db, None, "auto")
        logger.info(f"[scheduler] 플레이스 오늘 동기화 완료: {result}")
    except Exception as e:
        logger.error(f"[scheduler] 플레이스 오늘 동기화 실패: {e}", exc_info=True)


async def _run_webpage_today_sync():
    """웹페이지 오늘 동기화 (매일 19:00 KST)."""
    logger.info("[scheduler] 웹페이지 오늘 동기화 시작 (auto)")
    try:
        import asyncio
        from webpage.sync_to_db import sync_all_to_db
        # AsyncIO loop 블로킹 방지
        result = await asyncio.to_thread(sync_all_to_db, None, "auto")
        logger.info(f"[scheduler] 웹페이지 오늘 동기화 완료: {result}")
    except Exception as e:
        logger.error(f"[scheduler] 웹페이지 오늘 동기화 실패: {e}", exc_info=True)


async def _run_rank_check_sync():
    """SB체커 자동 측정 (매일 20:00 KST)."""
    logger.info("[scheduler] SB체커 자동 측정 시작 (auto)")
    try:
        import asyncio
        from checker.place_rank import run_check_all
        # AsyncIO loop 블로킹 방지
        result = await asyncio.to_thread(run_check_all, "auto")
        logger.info(f"[scheduler] SB체커 자동 측정 완료: {result}")
    except Exception as e:
        logger.error(f"[scheduler] SB체커 자동 측정 실패: {e}", exc_info=True)


async def _run_daily_snapshot():
    """플레이스/웹페이지 일별 스냅샷 (매일 23:00)."""
    logger.info("[scheduler] 일별 스냅샷 시작")
    try:
        from place.daily_snapshot import take_snapshot as place_snap
        result = place_snap()
        logger.info(f"[scheduler] 플레이스 스냅샷: {result}")
    except Exception as e:
        logger.error(f"[scheduler] 플레이스 스냅샷 실패: {e}", exc_info=True)

    try:
        from webpage.daily_snapshot import take_snapshot as webpage_snap
        result = webpage_snap()
        logger.info(f"[scheduler] 웹페이지 스냅샷: {result}")
    except Exception as e:
        logger.error(f"[scheduler] 웹페이지 스냅샷 실패: {e}", exc_info=True)


def setup_scheduler():
    """스케줄러 잡 등록 + 시작."""
    scheduler.add_job(
        _run_blog_sync,
        CronTrigger(hour=6, minute=0),
        id="blog_daily_sync",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_place_today_sync,
        CronTrigger(hour=10, minute=30),
        id="place_morning_auto_sync",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_place_today_sync,
        CronTrigger(hour=18, minute=30),
        id="place_today_auto_sync",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_webpage_today_sync,
        CronTrigger(hour=11, minute=0),
        id="webpage_morning_auto_sync",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_webpage_today_sync,
        CronTrigger(hour=19, minute=0),
        id="webpage_today_auto_sync",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_rank_check_sync,
        CronTrigger(hour=20, minute=0),
        id="rank_check_auto_sync",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_daily_snapshot,
        CronTrigger(hour=23, minute=0),
        id="place_daily_snapshot",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("[scheduler] 스케줄러 시작 — 7개 잡 등록 완료")


# 잡 ID → 사람이 읽는 라벨. 백엔드가 단일 source — 프론트는 그대로 표시만.
_JOB_LABELS = {
    "blog_daily_sync": "블로그 노션",
    "place_morning_auto_sync": "플레이스 (오전)",
    "place_today_auto_sync": "플레이스 (오후)",
    "webpage_morning_auto_sync": "웹페이지 (오전)",
    "webpage_today_auto_sync": "웹페이지 (오후)",
    "rank_check_auto_sync": "SB체커",
    "place_daily_snapshot": "일별 스냅샷",
}


def get_scheduler_status():
    """스케줄러 상태 반환."""
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "label": _JOB_LABELS.get(job.id, job.id),
            "next_run": str(job.next_run_time) if job.next_run_time else None,
        })
    return {"running": scheduler.running, "jobs": jobs}
