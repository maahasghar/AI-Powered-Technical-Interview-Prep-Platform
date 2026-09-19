from app.audit import record_audit


class SubmissionsService:
    def __init__(self, submissions_repo, queue):
        self.submissions_repo = submissions_repo
        self.queue = queue

    def get_submission(self, submission_id: int):
        return self.submissions_repo.get_by_id(submission_id)

    def get_all_submissions(self, skip: int = 0, limit: int = 100):
        return self.submissions_repo.get_all(skip, limit)

    def get_user_submissions(self, user_id: int, skip: int = 0, limit: int = 100):
        return self.submissions_repo.get_by_user_id(user_id, skip, limit)

    def get_problem_submissions(self, problem_id: int, skip: int = 0, limit: int = 100):
        return self.submissions_repo.get_by_problem_id(problem_id, skip, limit)

    def create_submission(
        self,
        user_id: int,
        problem_id: int,
        code: str,
        language: str,
        status: str = "QUEUED",
    ):
        submission = self.submissions_repo.create(
            user_id, problem_id, code, language, status
        )
        record_audit(
            self.submissions_repo.db.session,
            "SUBMISSION_CREATED",
            actor_user_id=user_id,
            target_id=submission.id,
        )
        self.submissions_repo.db.commit()
        # The committed QUEUED row is also the durable dispatch record. The worker
        # reconciles it if Redis is unavailable or the API dies before enqueue.
        self.queue.enqueue(submission.id)
        return submission

    def update_submission(self, submission_id: int, **kwargs):
        return self.submissions_repo.update(submission_id, **kwargs)

    def delete_submission(self, submission_id: int):
        return self.submissions_repo.delete(submission_id)
