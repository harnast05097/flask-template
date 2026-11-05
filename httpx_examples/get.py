import httpx

response = httpx.get(
    "https://httpbin.org/get",
    params={"done": "0"},
    timeout=5.0,
)
response.raise_for_status()
print(response.status_code)
print(response.headers["content-type"])
print(response.json()["args"])
