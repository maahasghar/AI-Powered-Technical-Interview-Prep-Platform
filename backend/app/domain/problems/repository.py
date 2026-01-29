from app.domain.problems.models import Problem


class ProblemsRepository:
    def __init__(self, db):
        self.db = db

    def get_by_id(self, problem_id: int):
        return self.db.query(Problem).filter(Problem.id == problem_id).first()

    def get_all(self, skip: int = 0, limit: int = 100):
        return self.db.query(Problem).offset(skip).limit(limit).all()

    def get_by_difficulty(self, difficulty: int):
        return self.db.query(Problem).filter(Problem.difficulty == difficulty).all()

    def create(
        self,
        title: str,
        difficulty: int,
        categories: list,
        description: str,
        test_cases: str,
    ):
        problem = Problem(
            title=title,
            difficulty=difficulty,
            categories=categories,
            description=description,
            test_cases=test_cases,
        )
        self.db.add(problem)
        self.db.commit()
        self.db.refresh(problem)
        return problem

    def update(self, problem_id: int, **kwargs):
        problem = self.get_by_id(problem_id)
        if problem:
            for key, value in kwargs.items():
                setattr(problem, key, value)
            self.db.commit()
            self.db.refresh(problem)
        return problem

    def delete(self, problem_id: int):
        problem = self.get_by_id(problem_id)
        if problem:
            self.db.delete(problem)
            self.db.commit()
        return problem
