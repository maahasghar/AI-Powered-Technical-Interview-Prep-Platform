from types import SimpleNamespace

from app.domain.user.progress_service import ProgressService


def test_progress_unit_calculates_solve_rate_and_breakdowns():
    rows = [
        SimpleNamespace(status="PASSED", difficulty=1, categories=["arrays"], created_at=None),
        SimpleNamespace(status="FAILED", difficulty=1, categories=["arrays", "hashing"], created_at=None),
        SimpleNamespace(status="RUNTIME_ERROR", difficulty=3, categories=["hashing"], created_at=None),
    ]
    repository = SimpleNamespace(get_submission_rows=lambda user_id: rows)

    result = ProgressService(repository).get_progress(42)

    assert result.total_attempted == 3
    assert result.total_solved == 1
    assert result.solve_rate == round(1 / 3, 4)
    assert result.by_difficulty["1"].attempted == 2
    assert result.by_difficulty["1"].solved == 1
    assert result.by_category["hashing"].attempted == 2