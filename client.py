"""Python-клиент локального API. Сначала запустите Flask в другом терминале."""

import argparse

import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:5000")
    parser.add_argument("--add", metavar="TITLE", help="Создать задачу перед чтением списка")
    parser.add_argument("--done", choices=["0", "1"], help="Фильтр по выполнению")
    args = parser.parse_args()

    try:
        with httpx.Client(base_url=args.url, timeout=5.0) as client:
            if args.add is not None:
                response = client.post("/api/tasks", json={"title": args.add})
                response.raise_for_status()
                print("Создана задача:", response.json())

            params = {} if args.done is None else {"done": args.done}
            response = client.get("/api/tasks", params=params)
            response.raise_for_status()
            print("Статус:", response.status_code)
            print("Content-Type:", response.headers["content-type"])
            for task in response.json()["tasks"]:
                mark = "x" if task["done"] else " "
                print(f"[{mark}] {task['id']}: {task['title']}")
    except httpx.HTTPStatusError as error:
        parser.exit(1, f"Сервер вернул HTTP {error.response.status_code}.\n")
    except httpx.RequestError:
        parser.exit(1, "Не удалось подключиться. Проверьте адрес и запустите Flask.\n")


if __name__ == "__main__":
    main()
