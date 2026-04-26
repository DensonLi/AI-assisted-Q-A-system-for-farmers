from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationResponse(BaseModel):
    id: int
    title: str
    region_id: int
    crop_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetail(ConversationResponse):
    messages: list[MessageResponse] = []


class AskRequest(BaseModel):
    conversation_id: Optional[int] = None
    question: str


class AskResponse(BaseModel):
    conversation_id: int
    answer: str
    message_id: int
