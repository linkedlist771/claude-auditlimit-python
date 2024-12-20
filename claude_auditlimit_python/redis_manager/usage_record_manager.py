# usage_record_manager.py
from typing import Dict

from .usage_manager import UsageManager, TokenUsageStats


class UsageStats(TokenUsageStats):
    # 如果需要可以添加额外的统计字段
    pass



class UsageRecordManager(UsageManager):
    def _get_redis_key(self, identifier: str, period: str) -> str:
        # 只需要修改key前缀，从"token"改为"usage"
        return f"usage:{identifier}:{period}"

    # 可选：重命名方法使其更符合usage的语义
    async def increment_usage(self, identifier: str, count: int = 1) -> None:
        return await self.increment_token_usage(identifier, count)

    async def get_usage(self, identifier: str) -> UsageStats:
        stats = await self.get_token_usage(identifier)
        return UsageStats(**stats.dict())

    async def get_all_usage(self) -> Dict[str, UsageStats]:
        redis = await self.get_aioredis()
        keys = await redis.keys("usage:*:total")

        result = {}
        for key in keys:
            # Remove "usage:" prefix and ":total" suffix
            identifier = key[6:-6]
            stats = await self.get_usage(identifier)
            result[identifier] = stats

        return result
