import pytest
from app.domain.problems.models import Problem
from app.domain.submissions.models import Submission
from app.scripts.seed_problems import load_problems, seed_problems

from .conftest import auth_headers


@pytest.mark.parametrize("path", ["/api/v1/problems", "/api/v1/problems/1"])
def test_problem_reads_require_authentication(client, path):
    assert client.get(path).status_code == 401


@pytest.mark.parametrize("method", ["post", "patch", "delete"])
def test_problem_writes_require_authentication(client, method):
    path = "/api/v1/problems" if method == "post" else "/api/v1/problems/1"
    assert client.request(method, path, json={}).status_code == 401


def test_regular_user_can_read_but_cannot_manage(client, user_factory, problem_factory):
    headers = auth_headers(user_factory())
    problem = problem_factory()
    path = f"/api/v1/problems/{problem.id}"
    assert client.get(path, headers=headers).status_code == 200
    assert (
        client.patch(path, headers=headers, json={"title": "Changed"}).status_code
        == 403
    )
    assert (
        client.patch(path, headers=headers, json={"is_active": False}).status_code
        == 403
    )
    assert client.delete(path, headers=headers).status_code == 403
    assert (
        client.get(
            "/api/v1/problems?include_inactive=true", headers=headers
        ).status_code
        == 403
    )


def test_archive_preserves_submissions_and_can_be_restored(
    client, user_factory, problem_factory, db_session
):
    user = user_factory()
    user_headers = auth_headers(user)
    admin_headers = auth_headers(user_factory(email="admin@example.com", role="admin"))
    problem = problem_factory()
    path = f"/api/v1/problems/{problem.id}"
    payload = {"problem_id": problem.id, "code": "pass", "language": "python"}
    created = client.post("/api/v1/submissions", headers=user_headers, json=payload)
    assert created.status_code == 201
    submission_id = created.json()["id"]
    updated = client.patch(path, headers=admin_headers, json={"title": "Revised"})
    assert updated.status_code == 200
    assert updated.json()["title"] == "Revised"
    for _ in range(2):
        archived = client.delete(path, headers=admin_headers)
        assert archived.status_code == 200
        assert archived.json()["is_active"] is False
    assert db_session.get(Problem, problem.id) is not None
    assert db_session.get(Submission, submission_id).problem_id == problem.id
    assert (
        client.get(
            f"/api/v1/submissions/{submission_id}", headers=user_headers
        ).status_code
        == 200
    )
    assert client.get(path, headers=user_headers).status_code == 404
    assert client.get("/api/v1/problems", headers=user_headers).json() == []
    assert client.get(path, headers=admin_headers).json()["is_active"] is False
    assert (
        len(
            client.get(
                "/api/v1/problems?include_inactive=true", headers=admin_headers
            ).json()
        )
        == 1
    )
    assert (
        client.post(
            "/api/v1/submissions", headers=user_headers, json=payload
        ).status_code
        == 404
    )
    restored = client.patch(path, headers=admin_headers, json={"is_active": True})
    assert restored.status_code == 200
    assert restored.json()["is_active"] is True
    assert client.get(path, headers=user_headers).status_code == 200


def test_filters_combine_before_pagination(
    client, user_factory, problem_factory, db_session
):
    headers = auth_headers(user_factory())
    archived = problem_factory(categories=["arrays"])
    archived.is_active = False
    other = problem_factory(categories=["arrays"])
    other.difficulty = 2
    first = problem_factory(categories=["arrays"])
    second = problem_factory(categories=["arrays"])
    problem_factory(categories=["graphs"])
    db_session.commit()
    response = client.get(
        "/api/v1/problems?category=arrays&difficulty=1&skip=1&limit=1", headers=headers
    )
    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [second.id]
    assert first.id != second.id


@pytest.mark.parametrize(
    "field",
    ["title", "difficulty", "categories", "description", "test_cases", "is_active"],
)
def test_problem_update_rejects_null(client, user_factory, problem_factory, field):
    headers = auth_headers(user_factory(role="admin"))
    response = client.patch(
        f"/api/v1/problems/{problem_factory().id}", headers=headers, json={field: None}
    )
    assert response.status_code == 422


def test_missing_problem_returns_404(client, user_factory):
    headers = auth_headers(user_factory(role="admin"))
    assert client.get("/api/v1/problems/999", headers=headers).status_code == 404
    assert (
        client.patch(
            "/api/v1/problems/999", headers=headers, json={"title": "Missing"}
        ).status_code
        == 404
    )
    assert client.delete("/api/v1/problems/999", headers=headers).status_code == 404
    assert (
        client.post(
            "/api/v1/submissions",
            headers=headers,
            json={"problem_id": 999, "code": "pass"},
        ).status_code
        == 404
    )


def test_seeding_is_idempotent_and_preserves_admin_changes(db_session, problem_factory):
    custom = problem_factory(title="Custom problem")
    seeds = load_problems()
    assert 10 <= len(seeds) <= 20
    assert {problem["difficulty"] for problem in seeds} == {1, 2, 3}
    assert seed_problems(db_session) == len(seeds)
    db_session.commit()
    seeded = (
        db_session.query(Problem).filter(Problem.seed_key == seeds[0]["seed_key"]).one()
    )
    original_id = seeded.id
    seeded.title = "Admin revision"
    seeded.is_active = False
    db_session.commit()
    assert seed_problems(db_session) == 0
    db_session.commit()
    db_session.expire_all()
    assert seeded.id == original_id
    assert seeded.title == "Admin revision"
    assert seeded.is_active is False
    assert db_session.query(Problem).count() == len(seeds) + 1
    assert db_session.get(Problem, custom.id).title == "Custom problem"
