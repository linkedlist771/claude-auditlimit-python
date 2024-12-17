# usage_manager.py
import json
from datetime import datetime
import time
from typing import Dict, Optional
from pydantic import BaseModel

from claude_auditlimit_python.configs import REDIS_PORT, REDIS_HOST, REDIS_DB
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

    def __init__(self, host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB):
        super().__init__(host, port, db)

    def _get_redis_key(self, token: str, period: str) -> str:
        return f"token:{token}:{period}"

    async def increment_token_usage(self, token: str, count: int = 1) -> None:
        redis = await self.get_aioredis()

        # Increment total count
        await redis.incrby(self._get_redis_key(token, self.PERIOD_TOTAL), count)

        # For each limited time period, increment or create key with expiry
        for period, expiry in [
            (self.PERIOD_3HOURS, 3 * 3600),
            (self.PERIOD_12HOURS, 12 * 3600),
            (self.PERIOD_24HOURS, 24 * 3600),
            (self.PERIOD_WEEK, 7 * 24 * 3600),
        ]:
            key = self._get_redis_key(token, period)
            # Check if key exists
            exists = await redis.exists(key)
            if not exists:
                # Key doesn't exist, set initial value and expire
                # 使用 set 命令直接初始化值，并设置过期时间
                await redis.set(key, count, ex=expiry)
            else:
                # Key exists, just increment
                await redis.incrby(key, count)
                # 确保有效期仍然存在（可选，如果希望更新过期时间）
                await redis.expire(key, expiry)

    async def get_token_usage(self, token: str) -> TokenUsageStats:
        redis = await self.get_aioredis()

        total_key = self._get_redis_key(token, self.PERIOD_TOTAL)
        total_val = await redis.get(total_key)
        total = int(total_val) if total_val else 0

        # 使用pipeline一次性获取所有周期值
        pipe = redis.pipeline()
        pipe.get(self._get_redis_key(token, self.PERIOD_3HOURS))
        pipe.get(self._get_redis_key(token, self.PERIOD_12HOURS))
        pipe.get(self._get_redis_key(token, self.PERIOD_24HOURS))
        pipe.get(self._get_redis_key(token, self.PERIOD_WEEK))
        results = await pipe.execute()

        last_3_hours = int(results[0]) if results[0] else 0
        last_12_hours = int(results[1]) if results[1] else 0
        last_24_hours = int(results[2]) if results[2] else 0
        last_week = int(results[3]) if results[3] else 0

        return TokenUsageStats(
            total=total,
            last_3_hours=last_3_hours,
            last_12_hours=last_12_hours,
            last_24_hours=last_24_hours,
            last_week=last_week,
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
