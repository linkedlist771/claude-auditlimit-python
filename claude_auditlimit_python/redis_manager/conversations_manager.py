import json
from datetime import datetime
import time
from typing import Dict, Optional
from pydantic import BaseModel
from claude_auditlimit_python.configs import REDIS_PORT, REDIS_HOST, REDIS_DB
from claude_auditlimit_python.redis_manager.base_redis_manager import BaseRedisManager
from claude_auditlimit_python.schemas import Conversation, Message


class ConversationsManager(BaseRedisManager):
    def __init__(self, host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB):
        super().__init__(host, port, db)

    def _get_redis_key(self, apikey: str, uuid: str) -> str:
        """Generate Redis key for storing conversations"""
        return f"conversations:{apikey}:{str(uuid)}"

    async def get_conversation(self, apikey: str, uuid: str) -> Conversation:
        """
        Get conversation for specific apikey and uuid.
        If not exists, creates new empty conversation.
        """
        redis = await self.get_aioredis()
        key = self._get_redis_key(apikey, uuid)

        value = await redis.get(key)
        if value is None:
            # Key doesn't exist, create new conversation
            conversation = Conversation.create_default_empty_conversation()
            await redis.set(key, conversation.model_dump_json())
            return conversation

        return Conversation.model_validate_json(value)

    async def add_message(
        self, apikey: str, uuid: str, message: Message
    ) -> Conversation:
        """
        Add a new message to the conversation.
        Creates new conversation if it doesn't exist.
        """
        redis = await self.get_aioredis()
        key = self._get_redis_key(apikey, uuid)

        conversation = await self.get_conversation(apikey, uuid)
        conversation.messages.append(message)
        conversation.update_modified_time()

        await redis.set(key, conversation.model_dump_json())
        return conversation

    async def get_all_conversations(self, apikey: str) -> Dict[str, Conversation]:
        """
        Get all conversations for a specific apikey.
        Returns a dictionary with uuid as key and Conversation as value.
        """
        redis = await self.get_aioredis()
        pattern = f"conversations:{apikey}:*"
        keys = await redis.keys(pattern)

        result = {}
        for key in keys:
            if isinstance(key, bytes):
                key = key.decode()
            uuid = key.split(":")[-1]
            value = await redis.get(key)
            if value:
                conversation = Conversation.model_validate_json(value)
                result[uuid] = conversation

        return result
