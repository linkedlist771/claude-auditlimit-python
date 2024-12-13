# usage_manager.py
import json
from datetime import datetime
import time
from typing import Dict, Optional
from pydantic import BaseModel

from claude_auditlimit_python.configs import REDIS_PORT, REDIS_HOST
from claude_auditlimit_python.redis_manager.base_redis_manager import BaseRedisManager


class TokenUsageStats(BaseModel):
    total: int = 0
    last_3_hours: int = 0
    last_12_hours: int = 0
    last_24_hours: int = 0
    last_week: int = 0


class UsageManager(BaseRedisManager):
    # Time period constants
    PERIOD_3HOURS = "3h"
    PERIOD_12HOURS = "12h"
    PERIOD_24HOURS = "24h"
    PERIOD_WEEK = "1w"
    PERIOD_TOTAL = "total"

    def __init__(self, host=REDIS_HOST, port=REDIS_PORT, db=0):
        super().__init__(host, port, db)

    def _get_redis_key(self, token: str, period: str) -> str:
        return f"token:{token}:{period}"

    async def increment_token_usage(self, token: str, count: int = 1) -> None:
        redis = await self.get_aioredis()
        pipe = redis.pipeline()
        now = int(time.time())

        # Increment total count by the specified amount
        pipe.incrby(self._get_redis_key(token, self.PERIOD_TOTAL), count)

        # Add usage records for different time periods
        for period, expiry in [
            (self.PERIOD_3HOURS, 3 * 3600),
            (self.PERIOD_12HOURS, 12 * 3600),
            (self.PERIOD_24HOURS, 24 * 3600),
            (self.PERIOD_WEEK, 7 * 24 * 3600),
        ]:
            key = self._get_redis_key(token, period)
            # Add the count as the score instead of the timestamp
            pipe.zadd(key, {str(now): float(count)})
            pipe.expire(key, expiry)

        await pipe.execute()

    async def get_token_usage(self, token: str) -> TokenUsageStats:
        redis = await self.get_aioredis()
        pipe = redis.pipeline()
        now = int(time.time())

        # Calculate time boundaries
        three_hours_ago = now - 3 * 3600
        twelve_hours_ago = now - 12 * 3600
        twenty_four_hours_ago = now - 24 * 3600
        week_ago = now - 7 * 24 * 3600

        # Prepare commands
        total_key = self._get_redis_key(token, self.PERIOD_TOTAL)
        pipe.get(total_key)

        for period, time_ago in [
            (self.PERIOD_3HOURS, three_hours_ago),
            (self.PERIOD_12HOURS, twelve_hours_ago),
            (self.PERIOD_24HOURS, twenty_four_hours_ago),
            (self.PERIOD_WEEK, week_ago),
        ]:
            key = self._get_redis_key(token, period)
            # Sum the scores (counts) for entries after the time threshold
            pipe.zrangebyscore(key, time_ago, "+inf", withscores=True)

        results = await pipe.execute()

        # Calculate sums for each period
        period_sums = []
        for period_result in results[1:]:  # Skip the total count
            period_sum = sum(score for _, score in period_result)
            period_sums.append(int(period_sum))

        return TokenUsageStats(
            total=int(results[0] or 0),
            last_3_hours=period_sums[0],
            last_12_hours=period_sums[1],
            last_24_hours=period_sums[2],
            last_week=period_sums[3],
        )

    async def get_all_token_usage(self) -> Dict[str, TokenUsageStats]:
        redis = await self.get_aioredis()
        keys = await redis.keys("token:*:total")

        result = {}
        for key in keys:
            token = key[6:-6]  # Remove "token:" prefix and ":total" suffix
            stats = await self.get_token_usage(token)
            result[token] = stats

        return result

    async def cleanup_old_records(self) -> None:
        redis = await self.get_aioredis()
        now = int(time.time())

        time_periods = {
            self.PERIOD_3HOURS: now - 3 * 3600,
            self.PERIOD_12HOURS: now - 12 * 3600,
            self.PERIOD_24HOURS: now - 24 * 3600,
            self.PERIOD_WEEK: now - 7 * 24 * 3600,
        }

        for period, cutoff_time in time_periods.items():
            pattern = f"token:*:{period}"
            keys = await redis.keys(pattern)

            for key in keys:
                await redis.zremrangebyscore(key, "-inf", cutoff_time)
