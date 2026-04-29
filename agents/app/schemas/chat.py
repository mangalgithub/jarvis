from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    user_id: str = Field(default="default-user")
    message: str


class ChatResponse(BaseModel):
    reply: str
    actions: list[dict] = Field(default_factory=list)
