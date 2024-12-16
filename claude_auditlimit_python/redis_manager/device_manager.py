# device_manager.py
import hashlib
import json
from datetime import timedelta
from typing import List, Optional, Dict

from claude_auditlimit_python.configs import MAX_DEVICES
from claude_auditlimit_python.redis_manager.base_redis_manager import BaseRedisManager


class DeviceInfo:
    def __init__(self, user_agent: str, host: str):
        self.user_agent = user_agent
        self.host = host

    def to_dict(self) -> dict:
        return {"user_agent": self.user_agent, "host": self.host}

    @classmethod
    def from_dict(cls, data: dict) -> "DeviceInfo":
        return cls(user_agent=data.get("user_agent", ""), host=data.get("host", ""))


class DeviceManager(BaseRedisManager):
    DEVICE_EXPIRE = timedelta(days=2)

    def _generate_device_hash(self, identifier: str) -> str:
        return hashlib.sha256(identifier.encode()).hexdigest()

    def _get_device_key(self, token: str) -> str:
        return f"devices:{token}"

    def _get_device_info_key(self, token: str, device_hash: str) -> str:
        return f"device_info:{token}:{device_hash}"

    async def check_and_add_device(
        self, token: str, device_identifier: str, user_agent: str, host: str
    ) -> bool:
        device_hash = self._generate_device_hash(device_identifier)
        key = self._get_device_key(token)
        redis = await self.get_aioredis()

        # Check if device exists
        exists = await redis.sismember(key, device_hash)
        if exists:
            return True

        # Check device count
        count = await redis.scard(key)
        if count >= MAX_DEVICES:
            return False

        # Add device
        await redis.sadd(key, device_hash)

        # Store device info
        info = DeviceInfo(user_agent=user_agent, host=host)
        await self._store_device_info(token, device_hash, info)

        # Set expiration
        await redis.expire(key, int(self.DEVICE_EXPIRE.total_seconds()))
        return True

    async def _store_device_info(self, token: str, device_hash: str, info: DeviceInfo):
        key = self._get_device_info_key(token, device_hash)
        redis = await self.get_aioredis()

        await redis.hset(key, mapping=info.to_dict())
        await redis.expire(key, int(self.DEVICE_EXPIRE.total_seconds()))

    async def get_device_list(self, token: str) -> List[DeviceInfo]:
        key = self._get_device_key(token)
        redis = await self.get_aioredis()

        device_hashes = await redis.smembers(key)
        device_list = []

        for device_hash in device_hashes:
            info_key = self._get_device_info_key(token, device_hash)
            info = await redis.hgetall(info_key)
            if info:
                device_list.append(DeviceInfo.from_dict(info))

        return device_list

    async def remove_device(self, token: str, device_identifier: str) -> bool:
        device_hash = self._generate_device_hash(device_identifier)
        key = self._get_device_key(token)
        info_key = self._get_device_info_key(token, device_hash)
        redis = await self.get_aioredis()

        # Remove device info
        await redis.delete(info_key)

        # Remove device from set
        removed = await redis.srem(key, device_hash)
        return removed > 0

    async def get_all_token_devices(self) -> Dict[str, List[DeviceInfo]]:
        redis = await self.get_aioredis()
        keys = await redis.keys("devices:*")
        result = {}

        for key in keys:
            token = key[8:]  # Remove "devices:" prefix
            device_list = await self.get_device_list(token)
            result[token] = device_list

        return result
