# base_redis_manager.py
import json
from redis.asyncio import Redis
from claude_auditlimit_python.configs import REDIS_HOST, REDIS_PORT


class BaseRedisManager:
    def __init__(self, host=REDIS_HOST, port=REDIS_PORT, db=0):
        """Initialize the connection to Redis."""
        self.host = host
        self.port = port
        self.db = db
        self.aioredis = None

    async def get_aioredis(self):
        if self.aioredis is None:
            self.aioredis = await Redis.from_url(
                f"redis://{self.host}:{self.port}/{self.db}", decode_responses=True
            )
        return self.aioredis

    async def decoded_get(self, key):
        res = await (await self.get_aioredis()).get(key)
        if isinstance(res, bytes):
            res = res.decode("utf-8")
        return res

    async def get_dict_value_async(self, key):
        value = await self.decoded_get(key)
        if value is None:
            return {}
        try:
            res = json.loads(value)
            if not isinstance(res, dict):
                return {}
            else:
                return res
        except (json.JSONDecodeError, TypeError):
            return {}

    async def set_async(self, key, value):
        await (await self.get_aioredis()).set(key, value)

    async def exists_async(self, key):
        return await (await self.get_aioredis()).exists(key)
