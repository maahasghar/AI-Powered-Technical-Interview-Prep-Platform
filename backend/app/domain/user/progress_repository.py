from sqlalchemy import select

from app.domain.problems.models import Problem
from app.domain.submissions.models import Submission


class ProgressRepository:
    def __init__(self, session):
        self.session = session

    def get_submission_rows(self, user_id: int):
        return self.session.execute(
            select(
                Submission.status,
                Submission.created_at,
                Problem.difficulty,
                Problem.categories,
            )
            .join(Problem, Problem.id == Submission.problem_id)
            .where(Submission.user_id == user_id)
            .order_by(Submission.created_at.desc(), Submission.id.desc())
        ).all()