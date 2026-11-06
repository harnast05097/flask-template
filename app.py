"""Учебный список задач с HTML-формой и JSON API.

Как Flask обрабатывает запрос:

1. Сервер принимает HTTP-запрос и вызывает объект app через WSGI,
   стандартный интерфейс между сервером и Python-приложением.
2. Flask делает данные текущего запроса доступными через request
   и выбирает обработчик по HTTP-методу и пути.
3. Обработчик читает данные запроса и возвращает результат.
   Например, task_list() возвращает HTML из Jinja, а api_task_list()
   возвращает словарь.
4. Flask собирает HTTP-ответ. Словарь становится JSON, а пара
   (словарь, 201) задаёт и тело ответа, и код статуса.
"""

from pathlib import Path

from flask import Flask, abort, redirect, render_template, request, url_for

from db import get_db, init_app

# Объект app хранит настройки и маршруты. Имя модуля помогает Flask
# найти папки templates и static.
app = Flask(__name__)
app.config["DATABASE"] = Path(app.instance_path) / "tasks.sqlite3"
init_app(app)

MAX_TITLE_LENGTH = 120


def read_tasks(done=None):
    if done is None:
        return get_db().execute(
            "SELECT id, title, done FROM task ORDER BY id DESC"
        ).fetchall()
    return get_db().execute(
        "SELECT id, title, done FROM task WHERE done = ? ORDER BY id DESC",
        (done,),
    ).fetchall()


def title_error(title):
    if not isinstance(title, str) or not title.strip():
        return "Введите название задачи."
    if len(title.strip()) > MAX_TITLE_LENGTH:
        return f"Название должно содержать не больше {MAX_TITLE_LENGTH} символов."
    return None


def save_task(title):
    db = get_db()
    cursor = db.execute("INSERT INTO task (title) VALUES (?)", (title.strip(),))
    db.commit()
    return cursor.lastrowid


def task_json(task):
    return {"id": task["id"], "title": task["title"], "done": bool(task["done"])}


@app.get("/")
def index():
    return redirect(url_for("task_list"))


# При загрузке модуля декоратор регистрирует task_list как обработчик GET /tasks.
@app.get("/tasks")
def task_list():
    # Flask передаёт задачи из SQLite в шаблон Jinja templates/tasks.html.
    # В шаблоне список доступен как переменная tasks. Результат — HTML.
    status = request.args.get("status", "all")
    if status == "active":
        done_filter = 0
    elif status == "completed":
        done_filter = 1
    else:
        status = "all"
        done_filter = None

    return render_template("tasks.html", tasks=read_tasks(done_filter),
        max_title_length=MAX_TITLE_LENGTH,
        current_status=status
    )


@app.post("/tasks")
def task_create():
    title = request.form.get("title", "")
    error = title_error(title)
    if error:
        # Снова рендерим шаблон Jinja, сохраняя введённый текст и показывая ошибку.
        return render_template(
            "tasks.html",
            tasks=read_tasks(),
            title=title,
            error=error,
            max_title_length=MAX_TITLE_LENGTH,
            current_status="all"
        ), 400
    save_task(title)
    # После POST браузер получает адрес страницы, которую нужно запросить GET.
    return redirect(url_for("task_list"), code=303)


@app.post("/tasks/<int:task_id>/toggle")
def task_toggle(task_id):
    db = get_db()
    cursor = db.execute("UPDATE task SET done = 1 - done WHERE id = ?", (task_id,))
    if cursor.rowcount == 0:
        abort(404)
    db.commit()
    return redirect(request.referrer or url_for("task_list"), code=303)


@app.get("/api/tasks")
def api_task_list():
    done = request.args.get("done")
    if done not in (None, "0", "1"):
        return {"error": "Параметр done должен быть 0 или 1."}, 400
    tasks = read_tasks(None if done is None else int(done))
    return {"tasks": [task_json(task) for task in tasks]}


@app.post("/api/tasks")
def api_task_create():
    if not request.is_json:
        return {"error": "Отправьте JSON с Content-Type: application/json."}, 415
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return {"error": "Тело запроса должно быть JSON-объектом."}, 400
    title = data.get("title")
    error = title_error(title)
    if error:
        return {"error": error}, 400
    task_id = save_task(title)
    return {"id": task_id, "title": title.strip(), "done": False}, 201


@app.get("/api/tasks/<int:task_id>")
def api_get_task(task_id):
    task = get_db().execute(
        "SELECT id, title, done FROM task WHERE id = ?", (task_id,)
    ).fetchone()
    if task is None:
        abort(404)
    return task_json(task)


@app.delete("/api/tasks/<int:task_id>")
def api_delete_task(task_id):
    db = get_db()
    cursor = db.execute("DELETE FROM task WHERE id = ?", (task_id,))
    if cursor.rowcount == 0:
        abort(404)
    db.commit()
    return "", 204


if __name__ == "__main__":
    app.run(load_dotenv=False)
