from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import engine, get_db
from app import models, crud, schemas

models.Base.metadata.create_all(bind=engine)

BASE_URL = "https://scurto.onrender.com"

app = FastAPI(title="URL Shortener")

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def serve_frontend():
    return FileResponse("static/index.html")


@app.post("/shorten", response_model=schemas.ShortenResponse, status_code=201)
def shorten_url(request: schemas.ShortenRequest, db: Session = Depends(get_db)):
    long_url = str(request.long_url)
    url = crud.create_short_url(db, long_url)
    return schemas.ShortenResponse(
        short_code = url.short_code,
        short_url  = f"{BASE_URL}/{url.short_code}",
        long_url   = url.long_url,
        created_at = url.created_at,
    )


@app.get("/stats/{short_code}", response_model=schemas.StatsResponse)
def get_stats(short_code: str, db: Session = Depends(get_db)):
    url = crud.get_url_by_code(db, short_code)
    if not url:
        raise HTTPException(status_code=404, detail="Short URL not found")
    return url


@app.get("/{short_code}")
def redirect_url(short_code: str, db: Session = Depends(get_db)):
    url = crud.get_url_by_code(db, short_code)
    if not url:
        raise HTTPException(status_code=404, detail="Short URL not found")
    crud.increment_click(db, url)
    return RedirectResponse(url=url.long_url, status_code=302)



#python -m uvicorn app.main:app --reload
