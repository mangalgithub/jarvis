from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "Jarvis Agent Service"


settings = Settings()
