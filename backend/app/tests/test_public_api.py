from .conftest import auth_headers


def test_list_problems_and_filter_by_category(client, problem_factory):
    problem_factory(categories=["two-pointers"])
    problem_factory(
        title="Window Maximum",
        categories=["sliding-window"],
    )

    response = client.get("/api/v1/problems?category=two-pointers")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["categories"] == ["two-pointers"]


def test_non_admin_cannot_create_problem(client, user_factory):
    user = user_factory()

    response = client.post(
        "/api/v1/problems",
        headers=auth_headers(user),
        json={
            "title": "Unauthorized problem",
            "difficulty": 1,
            "categories": ["arrays"],
            "description": "Should not be created.",
            "test_cases": "[]",
        },
    )

    assert response.status_code == 403


def test_admin_can_create_problem(client, user_factory):
    admin = user_factory(email="admin@example.com", role="admin")

    response = client.post(
        "/api/v1/problems",
        headers=auth_headers(admin),
        json={
            "title": "Admin problem",
            "difficulty": 2,
            "categories": ["graphs"],
            "description": "Created by an admin.",
            "test_cases": "[]",
        },
    )

    assert response.status_code == 201
    assert response.json()["title"] == "Admin problem"


def test_user_can_create_and_list_own_submissions(
    client,
    user_factory,
    problem_factory,
):
    user = user_factory()
    problem = problem_factory()

    create_response = client.post(
        "/api/v1/submissions",
        headers=auth_headers(user),
        json={
            "problem_id": problem.id,
            "code": "print('hello')",
            "language": "python",
        },
    )
    list_response = client.get(
        "/api/v1/submissions/me",
        headers=auth_headers(user),
    )

    assert create_response.status_code == 201
    assert create_response.json()["status"] == "pending"
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


def test_admin_can_list_all_submissions(
    client,
    user_factory,
    problem_factory,
):
    user = user_factory()
    admin = user_factory(email="admin@example.com", role="admin")
    problem = problem_factory()

    client.post(
        "/api/v1/submissions",
        headers=auth_headers(user),
        json={
            "problem_id": problem.id,
            "code": "print('hello')",
            "language": "python",
        },
    )

    response = client.get(
        "/api/v1/submissions/me",
        headers=auth_headers(admin),
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["user_id"] == user.id