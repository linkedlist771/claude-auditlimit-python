import json
from datetime import datetime
import time
from typing import Dict, Optional
from pydantic import BaseModel
from claude_auditlimit_python.configs import REDIS_PORT, REDIS_HOST, REDIS_DB
from claude_auditlimit_python.redis_manager.base_redis_manager import BaseRedisManager


class TokenUsageManager(BaseRedisManager):
    def __init__(self, host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB):
        super().__init__(host, port, db)

    def _get_redis_key(self, apikey: str, uuid: str) -> str:
        """Generate Redis key for storing token usage"""
        return f"token_usage:{apikey}:{str(uuid)}"

    async def get_token_usage(self, apikey: str, uuid: str) -> int:
        """
        Get token usage for specific apikey and uuid.
        If not exists, creates new entry with value 0.
        """
        redis = await self.get_aioredis()
        key = self._get_redis_key(apikey, uuid)

        value = await redis.get(key)
        if value is None:
            # Key doesn't exist, create new with value 0
            await redis.set(key, 0)
            return 0

        return int(value)

    async def increment_token_usage(self, apikey: str, uuid: str, increment: int = 1) -> int:
        """
        Increment token usage for specific apikey and uuid by given amount.
        Returns new value after increment.
        """
        redis = await self.get_aioredis()
        key = self._get_redis_key(apikey, uuid)

        # Check if key exists
        exists = await redis.exists(key)
        if not exists:
            # Key doesn't exist, set initial value
            await redis.set(key, increment)
            return increment

        # Increment existing value
        new_value = await redis.incrby(key, increment)
        return new_value

    async def get_all_token_usage(self, apikey: Optional[str] = None) -> Dict[str, Dict[str, int]]:
        """
        Get all token usages.
        If apikey is provided, get all uuid token usages for that apikey.
        If apikey is None, get all token usages for all apikeys.

        Returns:
        - When apikey provided: Dict[uuid_str, usage_count]
        - When apikey is None: Dict[apikey, Dict[uuid_str, usage_count]]
        """
        redis = await self.get_aioredis()

        if apikey:
            # Get usage for specific apikey
            pattern = f"token_usage:{apikey}:*"
            keys = await redis.keys(pattern)

            result = {}
            for key in keys:
                # Split key into components
                if isinstance(key, bytes):
                    key = key.decode()
                uuid_str = key.split(":")[-1]
                value = await redis.get(key)
                result[uuid_str] = int(value) if value else 0

            return result
        else:
            # Get usage for all apikeys
            pattern = "token_usage:*"
            keys = await redis.keys(pattern)

            result = {}
            for key in keys:
                # Split key into components
                if isinstance(key, bytes):
                    key = key.decode()
                key_parts = key.split(":")
                if len(key_parts) == 3:  # Ensure key format is correct
                    current_apikey = key_parts[1]
                    uuid_str = key_parts[2]

                    # Initialize dict for apikey if not exists
                    if current_apikey not in result:
                        result[current_apikey] = {}

                    value = await redis.get(key)
                    result[current_apikey][uuid_str] = int(value) if value else 0

            return result

# # 初始化
# manager = TokenUsageManager()
#
# # 获取使用量(不存在会创建新记录)
# usage = await manager.get_token_usage("my_apikey", uuid_obj)
#
# # 增加使用量
# new_value = await manager.increment_token_usage("my_apikey", uuid_obj, 5)
#
# # 获取某个apikey下所有uuid的使用量
# all_usage = await manager.get_all_token_usage("my_apikey")
