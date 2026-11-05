import httpx

url = "https://httpbin.org/post"

form_response = httpx.post(
    url, data={"title": "Read HTTP"}, timeout=5.0
)
print(form_response.json()["form"])

json_response = httpx.post(
    url, json={"title": "Read HTTP"}, timeout=5.0
)
print(json_response.json()["json"])
