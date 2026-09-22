from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProgressBucket(BaseModel):
    attempted: int
    solved: int
    solve_rate: float


class ProgressActivity(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: str
    created_at: datetime | None


class ProgressResponse(BaseModel):
    total_attempted: int
    total_solved: int
    solve_rate: float
    by_difficulty: dict[str, ProgressBucket]
    by_category: dict[str, ProgressBucket]
    recent_activity: list[ProgressActivity]
