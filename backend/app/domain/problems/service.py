class ProblemsService:
    def __init__(self, problems_repo):
        self.problems_repo = problems_repo

    def get_problem(self, problem_id: int):
        return self.problems_repo.get_by_id(problem_id)

    def get_all_problems(self, skip: int = 0, limit: int = 100):
        return self.problems_repo.get_all(skip, limit)

    def get_problems_by_difficulty(self, difficulty: int):
        return self.problems_repo.get_by_difficulty(difficulty)

    def create_problem(
        self,
        title: str,
        difficulty: int,
        categories: list,
        description: str,
        test_cases: str,
    ):
        return self.problems_repo.create(
            title, difficulty, categories, description, test_cases
        )

    def update_problem(self, problem_id: int, **kwargs):
        return self.problems_repo.update(problem_id, **kwargs)

    def delete_problem(self, problem_id: int):
        return self.problems_repo.delete(problem_id)
