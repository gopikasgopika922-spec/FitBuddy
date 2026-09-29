from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Goal = Literal["weight loss", "muscle gain", "general wellness", "flexibility", "endurance"]
Intensity = Literal["low", "medium", "high"]


class UserInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    username: str = Field(..., min_length=1, max_length=120)
    user_id: str = Field(..., min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")
    age: int = Field(..., ge=13, le=100)
    weight: float = Field(..., gt=20, le=500)
    goal: Goal
    intensity: Intensity


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    user_id: str = Field(..., min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")
    feedback: str = Field(..., min_length=3, max_length=2000)

    @field_validator("feedback")
    @classmethod
    def feedback_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Feedback cannot be blank.")
        return value.strip()
