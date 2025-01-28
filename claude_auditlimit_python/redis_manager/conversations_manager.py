import json
from datetime import datetime
import time
from typing import Dict, Optional
from pydantic import BaseModel
from claude_auditlimit_python.configs import REDIS_PORT, REDIS_HOST, REDIS_DB
from claude_auditlimit_python.redis_manager.base_redis_manager import BaseRedisManager
from claude_auditlimit_python.schemas import Conversation, Message
from loguru import logger

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

    async def get_conversations(self, api_key: str, conversation_id: str = None):
        """
        Get conversations for a specific API key.
        If conversation_id is provided, returns that specific conversation.
        Otherwise returns all conversations for the API key.
        """
        try:
            if conversation_id:
                conversation = await self.get_conversation(api_key, conversation_id)
                # Convert datetime to timestamp for JSON serialization
                conv_dict = conversation.model_dump(mode='json')
                return conv_dict
            
            conversations = await self.get_all_conversations(api_key)
            # Convert all conversations' datetime to timestamps
            return {
                uuid: conv.model_dump(mode='json')
                for uuid, conv in conversations.items()
            }

        except Exception as e:
            logger.error(f"Error in get_conversations: {str(e)}")
            raise

    async def get_all_users_conversations(self) -> Dict[str, Dict[str, dict]]:
        """
        Get all conversations for all users.
        Returns a nested dictionary with datetime fields serialized to JSON.
        """
        redis = await self.get_aioredis()
        pattern = "conversations*"
        keys = await redis.keys(pattern)
        logger.debug(f"all conversations keys:\n{keys}")
        result = {}
        
        for key in keys:
            if isinstance(key, bytes):
                key = key.decode()
            
            # Split key into components (conversations:apikey:uuid)
            _, apikey, uuid = key.split(":")
            
            value = await redis.get(key)
            if value:
                conversation = Conversation.model_validate_json(value)
                
                # Initialize dict for apikey if not exists
                if apikey not in result:
                    result[apikey] = {}
                    
                # Convert datetime to JSON serializable format
                result[apikey][uuid] = conversation.model_dump(mode='json')

        return result
