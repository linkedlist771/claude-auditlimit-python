from contextlib import asynccontextmanager
from loguru import logger
from fastapi import FastAPI

from claude_auditlimit_python.periodic_checks.limit_sheduler import LimitScheduler
from claude_auditlimit_python.utils.time_zone_utils import set_cn_time_zone


async def on_startup():
    logger.info("Starting up")
    set_cn_time_zone()
    logger.info("Clients loaded")
    await LimitScheduler.start()
    logger.info("Scheduler started")


async def on_shutdown():
    logger.info("Shutting down")
    await LimitScheduler.shutdown()
    logger.info("Scheduler stopped")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await on_startup()
    yield
    await on_shutdown()
