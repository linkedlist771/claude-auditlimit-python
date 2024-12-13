from datetime import datetime

from claude_auditlimit_python.configs import CLAUDE_CLIENT_LIMIT_CHECKS_INTERVAL_MINUTES
from claude_auditlimit_python.periodic_checks.clients_limit_checks import (
    periodic_tasks,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

limit_check_scheduler = AsyncIOScheduler()

# 设置定时任务
limit_check_scheduler.add_job(
    periodic_tasks,
    trigger=IntervalTrigger(minutes=CLAUDE_CLIENT_LIMIT_CHECKS_INTERVAL_MINUTES),
    id="check_usage_limits",
    name=f"Check API usage limits every {CLAUDE_CLIENT_LIMIT_CHECKS_INTERVAL_MINUTES} minutes",
    replace_existing=True,
)


class LimitScheduler:
    limit_check_scheduler = limit_check_scheduler

    @staticmethod
    async def start():
        # await check_reverse_official_usage_limits()
        limit_check_scheduler.start()

    @staticmethod
    async def shutdown():
        limit_check_scheduler.shutdown()
