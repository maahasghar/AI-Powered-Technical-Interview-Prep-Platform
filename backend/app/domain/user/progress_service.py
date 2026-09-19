from collections import defaultdict

from app.domain.user.progress_schemas import (
    ProgressActivity,
    ProgressBucket,
    ProgressResponse,
)


SOLVED_STATUS = "PASSED"


def _bucket(rows):
    attempted = len(rows)
    solved = sum(row.status == SOLVED_STATUS for row in rows)
    return ProgressBucket(
        attempted=attempted,
        solved=solved,
        solve_rate=round(solved / attempted, 4) if attempted else 0.0,
    )


class ProgressService:
    def __init__(self, repository):
        self.repository = repository

    def get_progress(self, user_id: int) -> ProgressResponse:
        rows = self.repository.get_submission_rows(user_id)
        by_difficulty = defaultdict(list)
        by_category = defaultdict(list)
        for row in rows:
            if row.difficulty is not None:
                by_difficulty[str(row.difficulty)].append(row)
            for category in row.categories or []:
                by_category[category].append(row)

        total_attempted = len(rows)
        total_solved = sum(row.status == SOLVED_STATUS for row in rows)
        return ProgressResponse(
            total_attempted=total_attempted,
            total_solved=total_solved,
            solve_rate=round(total_solved / total_attempted, 4)
            if total_attempted
            else 0.0,
            by_difficulty={
                key: _bucket(value) for key, value in sorted(by_difficulty.items())
            },
            by_category={
                key: _bucket(value) for key, value in sorted(by_category.items())
            },
            recent_activity=[
                ProgressActivity(status=row.status, created_at=row.created_at)
                for row in rows[:10]
            ],
        )