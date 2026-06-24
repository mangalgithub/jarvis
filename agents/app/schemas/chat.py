from pydantic import BaseModel, Field, field_validator
from app.core.guardrails import validate_image_input


class ChatRequest(BaseModel):
    user_id: str = Field(default="default-user")
    message: str
    image: str | None = None

    @field_validator("message")
    @classmethod
    def validate_message_length(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Message cannot be empty")
        # Length truncation will happen in the orchestrator via sanitize_input,
        # but we can do a preliminary check here if we want to reject entirely.
        return v

    @field_validator("image")
    @classmethod
    def validate_image(cls, v: str | None) -> str | None:
        if v is not None and not validate_image_input(v):
            raise ValueError("Invalid image format or size")
        return v


class ChatResponse(BaseModel):
    reply: str
    actions: list[dict] = Field(default_factory=list)

