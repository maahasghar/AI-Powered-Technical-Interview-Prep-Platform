from pydantic import BaseModel, Field


class ProblemBase(BaseModel):
	title: str
	difficulty: int = Field(ge=1, le=3)
	categories: list[str] = Field(default_factory=list)
	description: str
	test_cases: str


class ProblemCreate(ProblemBase):
	pass


class ProblemUpdate(BaseModel):
	title: str | None = None
	difficulty: int | None = Field(default=None, ge=1, le=3)
	categories: list[str] | None = None
	description: str | None = None
	test_cases: str | None = None


class ProblemResponse(ProblemBase):
	id: int

	model_config = {"from_attributes": True}
