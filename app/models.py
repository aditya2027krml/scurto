from sqlalchemy import Column, String, BigInteger, DateTime, func
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

class Url(Base):
    __tablename__ = "urls"

    short_code    = Column(String(7),   primary_key=True, index=True)
    long_url      = Column(String(2048), nullable=False)
    long_url_hash = Column(String(32),   nullable=False, index=True)
    click_count   = Column(BigInteger,   default=0, nullable=False)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())