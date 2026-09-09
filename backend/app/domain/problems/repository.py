from app.domain.problems.models import Problem


class ProblemsRepository:
    def __init__(self, db):
        self.db = db

    def get_by_id(self, problem_id: int):
        return self.db.query(Problem).filter(Problem.id == problem_id).first()

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        *,
        difficulty=None,
        category=None,
        include_inactive: bool = False,
    ):
        query = self.db.query(Problem)
        if not include_inactive:
            query = query.filter(Problem.is_active.is_(True))
        if difficulty is not None:
            query = query.filter(Problem.difficulty == difficulty)
        if category is not None:
            query = query.filter(Problem.categories.any(category))
        return query.order_by(Problem.id).offset(skip).limit(limit).all()

    def get_by_difficulty(self, difficulty: int):
        return self.get_all(difficulty=difficulty)

    def get_by_category(self, category: str):
        return self.get_all(category=category)

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

    def archive(self, problem_id: int):
        return self.update(problem_id, is_active=False)
