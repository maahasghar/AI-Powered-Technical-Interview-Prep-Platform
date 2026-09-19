from datetime import datetime, timedelta, timezone

from app.domain.submissions.models import Submission
from app.domain.auth.models import AuthToken
from app.domain.auth.token_models import AccountToken
from app.domain.user.models import UserProfile
from app.feedback.models import Feedback
from app.domain.user.progress_service import ProgressService


def test_progress_service_aggregates_rows_without_submissions():
    repository = type("Repository", (), {"get_submission_rows": lambda self, user_id: []})()

    result = ProgressService(repository).get_progress(7)

    assert result.total_attempted == 0
    assert result.total_solved == 0
    assert result.solve_rate == 0.0
    assert result.by_difficulty == {}
    assert result.by_category == {}


def test_progress_endpoint_is_user_scoped(client, user_factory, problem_factory, db_session):
    first = user_factory(email="first@example.com")
    other = user_factory(email="other@example.com")
    problem = problem_factory(difficulty=2, categories=["arrays", "hashing"])
    db_session.add_all([
        Submission(user_id=first.id, problem_id=problem.id, code="pass", language="python", status="PASSED"),
        Submission(user_id=first.id, problem_id=problem.id, code="pass", language="python", status="FAILED"),
        Submission(user_id=other.id, problem_id=problem.id, code="pass", language="python", status="PASSED"),
    ])
    db_session.commit()

    from .conftest import auth_headers

    response = client.get("/api/v1/users/me/progress", headers=auth_headers(first))

    assert response.status_code == 200
    assert response.json()["total_attempted"] == 2
    assert response.json()["total_solved"] == 1
    assert response.json()["by_difficulty"]["2"]["attempted"] == 2
    assert response.json()["by_category"]["arrays"]["solved"] == 1


def test_account_deletion_removes_owned_data_but_keeps_problem(
    client, user_factory, problem_factory, db_session
):
    user = user_factory()
    problem = problem_factory()
    submission = Submission(
        user_id=user.id, problem_id=problem.id, code="pass", language="python", status="FAILED"
    )
    db_session.add(submission)
    db_session.commit()
    db_session.add_all([
        UserProfile(user_id=user.id, full_name="Candidate"),
        AuthToken(user_id=user.id, token_hash="refresh-hash", family_id="family"),
        AccountToken(
            user_id=user.id,
            token_hash="account-hash",
            token_type="reset",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        ),
    ])
    db_session.commit()
    db_session.add(Feedback(submission_id=submission.id, stage="DIAGNOSIS", status="FAILED"))
    db_session.commit()
    submission_id = submission.id

    from .conftest import auth_headers

    response = client.delete("/api/v1/users/me", headers=auth_headers(user))

    assert response.status_code == 204
    assert db_session.get(type(user), user.id) is None
    assert db_session.get(type(problem), problem.id) is not None
    assert db_session.query(Submission).filter_by(user_id=user.id).count() == 0
    assert db_session.query(Feedback).filter_by(submission_id=submission_id).count() == 0