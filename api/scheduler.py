"""백그라운드 스케줄러 — APScheduler 기반.

- 블로그 노션 동기화: 매일 06:00 KST
- 플레이스 오늘 동기화: 매일 15:00 KST
- 플레이스/웹페이지 일별 스냅샷: 매일 23:00 KST
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger("scheduler")

scheduler = AsyncIOScheduler(timezone="Asia/Seoul")


async def _run_blog_sync():
    """노션 → DB 블로그 동기화 (매일 06:00)."""
    logger.info("[scheduler] 블로그 동기화 시작")
    try:
        from blog.sync_notion import incremental_sync
        from blog.post_queries import get_notion_token, get_notion_db_id

        token = get_notion_token()
        db_id = get_notion_db_id()
        if not token or not db_id:
            logger.warning("[scheduler] 노션 토큰/DB ID 미설정 — 동기화 건너뜀")
            return

        result = incremental_sync(token, db_id)
        logger.info(f"[scheduler] 블로그 동기화 완료: {result}")
    except Exception as e:
        logger.error(f"[scheduler] 블로그 동기화 실패: {e}", exc_info=True)


async def _run_place_today_sync():
    """플레이스 오늘 동기화 (매일 15:00 KST)."""
    logger.info("[scheduler] 플레이스 오늘 동기화 시작 (auto)")
    try:
        import asyncio
        from place.sync_to_db import sync_all_to_db
        # AsyncIO loop 블로킹 방지
        result = await asyncio.to_thread(sync_all_to_db, None, "auto")
        logger.info(f"[scheduler] 플레이스 오늘 동기화 완료: {result}")
    except Exception as e:
        logger.error(f"[scheduler] 플레이스 오늘 동기화 실패: {e}", exc_info=True)


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
        CronTrigger(hour=15, minute=0),
        id="place_today_auto_sync",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_daily_snapshot,
        CronTrigger(hour=23, minute=0),
        id="place_daily_snapshot",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("[scheduler] 스케줄러 시작 — 3개 잡 등록 완료")


def get_scheduler_status():
    """스케줄러 상태 반환."""
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "next_run": str(job.next_run_time) if job.next_run_time else None,
        })
    return {"running": scheduler.running, "jobs": jobs}
