from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class ProblemBase(BaseModel):
    title: str
    difficulty: int = Field(ge=1, le=3)
    categories: list[str] = Field(default_factory=list)
    description: str
    test_cases: str


class ProblemCreate(ProblemBase):
    pass


class ProblemUpdate(BaseModel):
    is_active: bool | None = None
    title: str | None = None
    difficulty: int | None = Field(default=None, ge=1, le=3)
    categories: list[str] | None = None
    description: str | None = None
    test_cases: str | None = None

    @model_validator(mode="after")
    def reject_explicit_nulls(self):
        for field in self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class ProblemResponse(ProblemBase):
    id: int
    is_active: bool

    model_config = {"from_attributes": True}
