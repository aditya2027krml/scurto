from pydantic import BaseModel, HttpUrl
from datetime import datetime

class ShortenRequest(BaseModel):
    long_url: HttpUrl

class ShortenResponse(BaseModel):
    short_code: str
    short_url:  str
    long_url:   str
    created_at: datetime

class StatsResponse(BaseModel):
    short_code:  str
    long_url:    str
    click_count: int
    created_at:  datetime