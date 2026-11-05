import sqlite3
from contextlib import closing

import pytest

from app import MAX_TITLE_LENGTH, app as flask_app


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setitem(flask_app.config, "TESTING", True)
    monkeypatch.setitem(flask_app.config, "DATABASE", tmp_path / "tasks.sqlite3")
    result = flask_app.test_cli_runner().invoke(args=["init-db"])
    assert result.exit_code == 0, result.exception or result.output
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


def test_form_redirect_and_persistent_storage(app, client):
    response = client.post("/tasks", data={"title": "  Читать HTTP  "})
    assert response.status_code == 303
    assert response.headers["Location"] == "/tasks"

    # Новое соединение проверяет, что приложение записало данные на диск.
    with closing(sqlite3.connect(app.config["DATABASE"])) as db:
        assert db.execute("SELECT title FROM task").fetchall() == [("Читать HTTP",)]

    assert client.get("/tasks").status_code == 200
    assert len(client.get("/api/tasks").json["tasks"]) == 1


@pytest.mark.parametrize("title", ["", "   ", "x" * (MAX_TITLE_LENGTH + 1)])
def test_invalid_form_does_not_create_task(client, title):
    assert client.post("/tasks", data={"title": title}).status_code == 400
    assert client.get("/api/tasks").json == {"tasks": []}


def test_api_creation_toggle_and_filter(client):
    first = client.post("/api/tasks", json={"title": "Первая"})
    second = client.post("/api/tasks", json={"title": "Вторая"})
    assert first.status_code == 201
    assert second.status_code == 201

    task_id = first.json["id"]
    assert client.post(f"/tasks/{task_id}/toggle").status_code == 303
    assert client.get("/api/tasks?done=1").json["tasks"] == [
        {"id": task_id, "title": "Первая", "done": True}
    ]
    assert client.get("/api/tasks?done=0").json["tasks"] == [
        {"id": second.json["id"], "title": "Вторая", "done": False}
    ]
    assert client.get("/api/tasks?done=invalid").status_code == 400


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"title": None},
        {"title": 42},
        {"title": ["text"]},
        [],
        {"title": " "},
        {"title": "x" * (MAX_TITLE_LENGTH + 1)},
    ],
)
def test_api_rejects_invalid_json(client, payload):
    assert client.post("/api/tasks", json=payload).status_code == 400
    assert client.get("/api/tasks").json == {"tasks": []}


def test_api_rejects_malformed_json(client):
    response = client.post("/api/tasks", data="{", content_type="application/json")
    assert response.status_code == 400
    assert client.get("/api/tasks").json == {"tasks": []}


def test_api_rejects_form_data(client):
    assert client.post("/api/tasks", data={"title": "Read"}).status_code == 415
    assert client.get("/api/tasks").json == {"tasks": []}


def test_user_text_is_stored_and_html_escaped(client):
    title = "<script>alert('test')</script>"
    assert client.post("/tasks", data={"title": title}).status_code == 303
    html = client.get("/tasks").get_data(as_text=True)
    assert title not in html
    assert "&lt;script&gt;" in html
    assert client.get("/api/tasks").json["tasks"][0]["title"] == title


def test_missing_task_and_wrong_method(client):
    assert client.post("/tasks/999/toggle").status_code == 404
    assert client.get("/tasks/999/toggle").status_code == 405
    assert client.get("/missing").status_code == 404


def test_initialization_preserves_existing_tasks(app, client):
    assert client.post("/tasks", data={"title": "Сохранить"}).status_code == 303
    result = app.test_cli_runner().invoke(args=["init-db"])
    assert result.exit_code == 0, result.exception or result.output
    tasks = client.get("/api/tasks").json["tasks"]
    assert [task["title"] for task in tasks] == ["Сохранить"]
