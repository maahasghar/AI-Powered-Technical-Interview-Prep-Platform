"""Run from backend with: python -m app.scripts.seed_problems."""

import json
from pathlib import Path

from app.domain.problems.models import Problem
from app.domain.problems.schemas import ProblemCreate
from app.infrastructure.db import SessionLocal
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session


def load_problems() -> list[dict]:
    problems = json.loads(Path(__file__).with_name("seed_problems.json").read_text())
    keys = [problem["seed_key"] for problem in problems]
    if len(keys) != len(set(keys)) or any(not key for key in keys):
        raise ValueError("Seed keys must be nonempty and unique")
    for problem in problems:
        ProblemCreate.model_validate(problem)
        cases = json.loads(problem["test_cases"])
        if not cases or any(
            "input" not in case or "expected" not in case for case in cases
        ):
            raise ValueError("Each seed problem needs input/expected test cases")
    return problems


def seed_problems(session: Session) -> int:
    """Insert missing seeds atomically; preserve existing edits and archive state.

    The caller owns the transaction. A unique key and ON CONFLICT also make
    concurrent invocations safe.
    """
    statement = (
        insert(Problem)
        .values(load_problems())
        .on_conflict_do_nothing(index_elements=[Problem.seed_key])
        .returning(Problem.id)
    )
    return len(session.execute(statement).scalars().all())


def main() -> None:
    with SessionLocal.begin() as session:
        count = seed_problems(session)
    print(f"Inserted {count} seed problems; existing seeds were preserved.")


if __name__ == "__main__":
    main()
