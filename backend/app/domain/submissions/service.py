class SubmissionsService:
    def __init__(self, submissions_repo):
        self.submissions_repo = submissions_repo

    def get_submission(self, submission_id: int):
        return self.submissions_repo.get_by_id(submission_id)

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
        status: str = "pending",
    ):
        return self.submissions_repo.create(user_id, problem_id, code, language, status)

    def update_submission(self, submission_id: int, **kwargs):
        return self.submissions_repo.update(submission_id, **kwargs)

    def delete_submission(self, submission_id: int):
        return self.submissions_repo.delete(submission_id)
