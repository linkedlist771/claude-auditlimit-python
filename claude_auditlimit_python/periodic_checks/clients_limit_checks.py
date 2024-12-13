import asyncio
import time
from tqdm.asyncio import tqdm

from loguru import logger


async def periodic_tasks():
    tasks = []
    for task in tasks:
        _task = asyncio.create_task(task())
    return {"message": "Check started in background"}
