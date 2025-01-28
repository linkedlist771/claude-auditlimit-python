from pydantic import BaseModel, Field
from typing import Union, List, Dict
from enum import Enum
from datetime import datetime, UTC


"""
This is only for usage to contain the message for the conversations 
between the user and the assistant.
"""


class Message(BaseModel):
    attachments: Union[str, None] = None
    role: str
    content: str


class Conversation(BaseModel):
    messages: List[Message]
    created_time: datetime = Field(default_factory=lambda: datetime.now(UTC))
    modified_time: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def update_modified_time(self):
        """Update the modified_time to current UTC time"""
        self.modified_time = datetime.now(UTC)

    @classmethod
    def create_default_empty_conversation(cls) -> "Conversation":
        return cls(messages=[])
