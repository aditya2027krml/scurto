from sqlalchemy.orm import Session
from app.models import Url
from app.utils import generate_short_code, hash_long_url

def get_url_by_code(db: Session, short_code: str) -> Url | None:
    """Look up a URL by its short code."""
    return db.query(Url).filter(Url.short_code == short_code).first()

def get_url_by_hash(db: Session, long_url_hash: str) -> Url | None:
    """Check if this long URL was already shortened (deduplication)."""
    return db.query(Url).filter(Url.long_url_hash == long_url_hash).first()

def create_short_url(db: Session, long_url: str) -> Url:
    """
    Create a new short URL entry.
    If the same long URL was shortened before, return the existing one.
    """
    url_hash = hash_long_url(long_url)

    # Dedup check — same long URL returns same short code
    existing = get_url_by_hash(db, url_hash)
    if existing:
        return existing

    # Generate a unique short code (retry if collision)
    while True:
        code = generate_short_code()
        if not get_url_by_code(db, code):
            break

    db_url = Url(
        short_code    = code,
        long_url      = long_url,
        long_url_hash = url_hash,
        click_count   = 0,
    )
    db.add(db_url)
    db.commit()
    db.refresh(db_url)
    return db_url

def increment_click(db: Session, url: Url) -> None:
    """Increment click count each time a short URL is visited."""
    url.click_count += 1
    db.commit()