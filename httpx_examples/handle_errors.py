import httpx

try:
    response = httpx.get("https://httpbin.org/get", timeout=5.0)
    response.raise_for_status()
except httpx.HTTPStatusError as exc:
    print("HTTP-статус:", exc.response.status_code)
except httpx.RequestError:
    print("Не удалось выполнить запрос")
