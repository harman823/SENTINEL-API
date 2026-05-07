import asyncio
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test():
    response = client.post("/api/v1/github-inspect", json={"url": "https://github.com/harman823/SENTINEL-API"})
    print("STATUS:", response.status_code)
    if response.status_code != 200:
        print("ERROR:", response.text)
    else:
        print("SUCCESS!")

if __name__ == "__main__":
    test()
