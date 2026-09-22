from unittest.mock import Mock

from app.domain.submissions.results import CaseResult
from app.feedback.models import Feedback
from app.feedback.policy import StructuredFeedback
from app.feedback.worker import process_feedback
from app.judge.worker import process_submission
from sqlalchemy.orm import sessionmaker


def test_authenticated_practice_journey_reaches_result_feedback_and_history(
    client, user_factory, problem_factory, db_session
):
    user = user_factory(email="journey@example.com")
    problem = problem_factory(
        title="Increment",
        categories=["arrays"],
        test_cases='[{"input":{"value":1},"expected":2}]',
    )
    client.headers["X-Session-Request"] = "1"
    headers = {
        "Authorization": f"Bearer {client.post('/api/v1/auth/login', json={'email': user.email, 'password': 'password'}).json()['access_token']}"
    }

    problems = client.get("/api/v1/problems", headers=headers)
    assert problems.status_code == 200
    assert problems.json()[0]["title"] == "Increment"

    created = client.post(
        "/api/v1/submissions",
        headers=headers,
        json={"problem_id": problem.id, "code": "def solve(value): return value + 1"},
    )
    assert created.status_code == 201
    submission_id = created.json()["id"]
    assert created.json()["status"] == "QUEUED"

    runner = Mock()
    runner.run_case.return_value = CaseResult("PASSED", 2)
    factory = sessionmaker(bind=db_session.get_bind())
    process_submission(submission_id, runner, factory)

    result = client.get(f"/api/v1/submissions/{submission_id}", headers=headers)
    assert result.status_code == 200
    assert result.json()["status"] == "PASSED"
    assert result.json()["result"]["tests_passed"] == 1

    db_session.expire_all()
    feedback_row = db_session.query(Feedback).filter_by(submission_id=submission_id).one()
    provider = Mock()
    provider.generate.return_value = StructuredFeedback(
        strengths=["The function follows the requested contract."],
        likely_issue=None,
        hint=None,
        complexity={"time": "O(1)", "space": "O(1)"},
        next_step="Keep checking edge cases.",
    ).model_dump_json()
    process_feedback(feedback_row.id, provider, factory)
    db_session.expire_all()

    feedback = client.get(f"/api/v1/submissions/{submission_id}/feedback", headers=headers)
    assert feedback.status_code == 200
    assert feedback.json()["items"][0]["status"] == "READY"
    assert feedback.json()["items"][0]["feedback"]["strengths"]

    history = client.get("/api/v1/submissions/me", headers=headers)
    assert history.status_code == 200
    assert history.json()[0]["id"] == submission_id