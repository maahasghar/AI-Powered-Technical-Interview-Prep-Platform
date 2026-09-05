from app.domain.submissions.models import Submission


class SubmissionsRepository:
    def __init__(self, db):
        self.db = db

    def get_by_id(self, submission_id: int):
        return self.db.query(Submission).filter(Submission.id == submission_id).first()

    def get_all(self, skip: int = 0, limit: int = 100):
        return self.db.query(Submission).offset(skip).limit(limit).all()

    def get_by_user_id(self, user_id: int, skip: int = 0, limit: int = 100):
        return (
            self.db.query(Submission)
            .filter(Submission.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_problem_id(self, problem_id: int, skip: int = 0, limit: int = 100):
        return (
            self.db.query(Submission)
            .filter(Submission.problem_id == problem_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create(
        self,
        user_id: int,
        problem_id: int,
        code: str,
        language: str,
        status: str = "pending",
    ):
        submission = Submission(
            user_id=user_id,
            problem_id=problem_id,
            code=code,
            language=language,
            status=status,
        )
        self.db.add(submission)
        self.db.commit()
        self.db.refresh(submission)
        return submission

    def update(self, submission_id: int, **kwargs):
        submission = self.get_by_id(submission_id)
        if submission:
            for key, value in kwargs.items():
                setattr(submission, key, value)
            self.db.commit()
            self.db.refresh(submission)
        return submission

    def delete(self, submission_id: int):
        submission = self.get_by_id(submission_id)
        if submission:
            self.db.delete(submission)
            self.db.commit()
        return submission
