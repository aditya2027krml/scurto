from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import get_db
from app import models

# Use a separate in-memory SQLite DB for tests — never touches production
SQLALCHEMY_TEST_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_TEST_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
models.Base.metadata.create_all(bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_shorten_url():
    response = client.post("/shorten", json={
        "long_url": "https://github.com"
    })
    assert response.status_code == 201
    data = response.json()
    assert "short_code" in data
    assert "short_url"  in data
    assert len(data["short_code"]) == 7
    assert data["long_url"] == "https://github.com/"


def test_shorten_invalid_url():
    response = client.post("/shorten", json={
        "long_url": "not-a-valid-url"
    })
    assert response.status_code == 422


def test_deduplication():
    # Same URL shortened twice should return same short code
    r1 = client.post("/shorten", json={"long_url": "https://openai.com"})
    r2 = client.post("/shorten", json={"long_url": "https://openai.com"})
    assert r1.json()["short_code"] == r2.json()["short_code"]


def test_redirect():
    # Shorten a URL then hit the short code
    r = client.post("/shorten", json={"long_url": "https://python.org"})
    code = r.json()["short_code"]

    response = client.get(f"/{code}", follow_redirects=False)
    assert response.status_code == 302
    assert "python.org" in response.headers["location"]


def test_click_count_increments():
    r = client.post("/shorten", json={"long_url": "https://fastapi.tiangolo.com"})
    code = r.json()["short_code"]

    # Hit the redirect 3 times
    for _ in range(3):
        client.get(f"/{code}", follow_redirects=False)

    stats = client.get(f"/stats/{code}")
    assert stats.json()["click_count"] == 3


def test_stats_endpoint():
    r = client.post("/shorten", json={"long_url": "https://sqlalchemy.org"})
    code = r.json()["short_code"]

    stats = client.get(f"/stats/{code}")
    assert stats.status_code == 200
    data = stats.json()
    assert data["short_code"]  == code
    assert data["click_count"] == 0


def test_stats_not_found():
    response = client.get("/stats/zzzzzzz")
    assert response.status_code == 404


def test_global_stats():
    response = client.get("/stats/global")
    assert response.status_code == 200
    data = response.json()
    assert "total_urls"   in data
    assert "total_clicks" in data