from datetime import datetime

from pydantic import BaseModel, Field


class SubmissionCreate(BaseModel):
	problem_id: int
	code: str
	language: str = Field(default="python")


class SubmissionUpdate(BaseModel):
	code: str | None = None
	language: str | None = None
	status: str | None = None
	result: str | None = None


class SubmissionResponse(BaseModel):
	id: int
	user_id: int
	problem_id: int
	code: str
	language: str
	status: str
	result: str | None = None
	created_at: datetime | None = None
	updated_at: datetime | None = None

	model_config = {"from_attributes": True}
