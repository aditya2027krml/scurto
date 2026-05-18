# Scurto — URL Shortener

> Short links. Big impact.

A production-ready URL shortener built with FastAPI and Python.  
**Live demo → [scurto.onrender.com](https://scurto.onrender.com)**

![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-teal?style=flat-square&logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue?style=flat-square&logo=postgresql)
![Render](https://img.shields.io/badge/Deployed-Render-purple?style=flat-square)

---

## Features

- **URL Shortening** — converts any long URL into a 7-character short code
- **Instant Redirect** — HTTP 302 redirect with sub-10ms response time
- **Click Analytics** — tracks total clicks per short URL in real time
- **Deduplication** — same long URL always returns the same short code
- **QR Code Generation** — auto-generated scannable QR for every short link
- **Clean UI** — dark-themed frontend with live URL preview and copy toast

---

## System Design

### Why 7 characters?

Using Base62 encoding (A-Z, a-z, 0-9 = 62 characters):
62^7 = 3,521,614,606,208 unique URLs (~3.5 trillion)

At 1,000 URLs/second, this covers **111 years** of traffic.

### Why UUID4 for ID generation?

- No clock dependency (timestamp-based IDs collide on Windows due to low timer resolution)
- Cryptographically random — IDs are not enumerable or guessable
- No coordination needed across servers — each instance generates its own IDs

### Why HTTP 302 over 301?

- **301 (Permanent):** browser caches the redirect — you lose all click analytics
- **302 (Temporary):** every click hits the server — click tracking works correctly

### Why MD5 for deduplication?

- MD5 of the long URL is stored as an indexed column
- On every write, we check `WHERE long_url_hash = md5(input)` before inserting
- Avoids full-text scanning a potentially large URL column

## Architecture

```
┌─────────────────────────────────────────────┐
│                   Client                    │
└─────────────────────┬───────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│            Load Balancer (Render)           │
└─────────────────────┬───────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│           FastAPI Web Server                │
│                                             │
│  POST /shorten                              │
│    └─▶ UUID4 → Base62 → DB Insert          │
│          └─▶ Return short URL              │
│                                             │
│  GET /{code}                                │
│    └─▶ DB Lookup → Increment Click         │
│          └─▶ HTTP 302 Redirect             │
└─────────────────────┬───────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│            PostgreSQL (Render)              │
│                                             │
│  urls                                       │
│  ├── short_code    VARCHAR(7)  PRIMARY KEY  │
│  ├── long_url      TEXT                     │
│  ├── long_url_hash VARCHAR(32) INDEX        │
│  ├── click_count   BIGINT                   │
│  └── created_at    TIMESTAMP                │
└─────────────────────────────────────────────┘
```

## Complete Request Workflow

```
╔═══════════════════════════════════════════════════════════════════╗
║                    SCURTO — REQUEST LIFECYCLE                     ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║   ┌─────────┐                                                     ║
║   │  USER   │                                                     ║
║   └────┬────┘                                                     ║
║        │                                                          ║
║        │  ① Pastes long URL into UI                              ║
║        ▼                                                          ║
║   ┌─────────────────────────────────────────────────────────┐    ║
║   │                  FRONTEND (index.html)                  │    ║
║   │  • Shows URL preview card (favicon + domain)            │    ║
║   │  • Validates URL starts with http/https                 │    ║
║   │  • Sends POST /shorten with { long_url }                │    ║
║   └────────────────────────┬────────────────────────────────┘    ║
║                            │                                      ║
║        ② POST /shorten     │                                      ║
║                            ▼                                      ║
║   ┌─────────────────────────────────────────────────────────┐    ║
║   │               FASTAPI — /shorten endpoint               │    ║
║   │                                                         │    ║
║   │  • Pydantic validates URL format                        │    ║
║   │  • Compute MD5(long_url) → url_hash                     │    ║
║   │  • Query DB: does url_hash already exist?               │    ║
║   │                                                         │    ║
║   │      YES ──────────────────────────────────────┐        │    ║
║   │       │                                        │        │    ║
║   │      NO                                        │        │    ║
║   │       │                                        │        │    ║
║   │       ▼                                        │        │    ║
║   │  • Generate UUID4 → Base62 → 7-char code       │        │    ║
║   │  • Insert row into PostgreSQL                  │        │    ║
║   │       │                                        │        │    ║
║   │       └──────────────────┬─────────────────────┘        │    ║
║   │                          ▼                              │    ║
║   │  • Return { short_url, short_code, created_at }         │    ║
║   └────────────────────────┬────────────────────────────────┘    ║
║                            │                                      ║
║        ③ 201 Created       │                                      ║
║                            ▼                                      ║
║   ┌─────────────────────────────────────────────────────────┐    ║
║   │                  FRONTEND (index.html)                  │    ║
║   │  • Displays short URL with copy button                  │    ║
║   │  • Generates QR code (qrcodejs library)                 │    ║
║   │  • Shows toast animation on copy                        │    ║
║   │  • Adds entry to Recent Links table                     │    ║
║   └────────────────────────┬────────────────────────────────┘    ║
║                            │                                      ║
║        ④ User shares / clicks short URL                          ║
║                            │                                      ║
║                            ▼                                      ║
║   ┌─────────────────────────────────────────────────────────┐    ║
║   │               FASTAPI — /{short_code}                   │    ║
║   │                                                         │    ║
║   │  • Lookup short_code in PostgreSQL (PK index → O(1))    │    ║
║   │  • Not found? → Return 404                              │    ║
║   │  • Found → Increment click_count                        │    ║
║   │  • Return HTTP 302 → Location: long_url                 │    ║
║   └────────────────────────┬────────────────────────────────┘    ║
║                            │                                      ║
║        ⑤ HTTP 302 Redirect │                                      ║
║                            ▼                                      ║
║   ┌─────────────────────────────────────────────────────────┐    ║
║   │              DESTINATION WEBSITE                        │    ║
║   │         User lands on the original URL                  │    ║
║   └─────────────────────────────────────────────────────────┘    ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

---

## Data Model

```
┌──────────────────────────────────────────────────────────────────┐
│                         TABLE: urls                              │
├─────────────────┬──────────────┬──────────────────────────────── ┤
│   Column        │   Type       │   Notes                         │
├─────────────────┼──────────────┼─────────────────────────────────┤
│ short_code      │ VARCHAR(7)   │ PRIMARY KEY — indexed, O(1)     │
│                 │              │ lookup on every redirect         │
├─────────────────┼──────────────┼─────────────────────────────────┤
│ long_url        │ TEXT         │ Original URL, max 2048 chars     │
├─────────────────┼──────────────┼─────────────────────────────────┤
│ long_url_hash   │ VARCHAR(32)  │ MD5 of long_url — INDEX         │
│                 │              │ used for deduplication checks    │
├─────────────────┼──────────────┼─────────────────────────────────┤
│ click_count     │ BIGINT       │ Incremented on every redirect    │
│                 │              │ default: 0                       │
├─────────────────┼──────────────┼─────────────────────────────────┤
│ created_at      │ TIMESTAMP    │ Auto-set on insert (UTC)         │
└─────────────────┴──────────────┴─────────────────────────────────┘

Indexes:
  ┌─────────────────────────────────────────────────────────────┐
  │  INDEX 1 → PRIMARY KEY (short_code)                        │
  │            Used on every GET /{code} redirect — O(1)       │
  ├─────────────────────────────────────────────────────────────┤
  │  INDEX 2 → long_url_hash                                   │
  │            Used on every POST /shorten for dedup check     │
  └─────────────────────────────────────────────────────────────┘

ID Generation Pipeline:
  ┌──────────┐    ┌──────────────┐    ┌─────────────┐    ┌────────┐
  │  UUID4   │───▶│  .int        │───▶│   Base62    │───▶│  [:7]  │
  │ 128-bit  │    │ large int    │    │   encode    │    │  code  │
  └──────────┘    └──────────────┘    └─────────────┘    └────────┘
  random UUID  →  integer value   →  62-char alphabet →  7 chars
```

---

## Tech Stack

| Layer      | Technology            |
| ---------- | --------------------- |
| Backend    | FastAPI + Python 3.11 |
| Database   | PostgreSQL (Render)   |
| ORM        | SQLAlchemy 2.0        |
| Server     | Uvicorn               |
| Frontend   | Vanilla HTML/CSS/JS   |
| Deployment | Render (Docker)       |

---

## API Reference

### POST /shorten

Creates a short URL.

**Request:**

```json
{
  "long_url": "https://example.com/very/long/path"
}
```

**Response `201 Created`:**

```json
{
  "short_code": "aB3xK9q",
  "short_url": "https://scurto.onrender.com/aB3xK9q",
  "long_url": "https://example.com/very/long/path",
  "created_at": "2026-05-18T12:00:00"
}
```

---

### GET /{short_code}

Redirects to the original URL with HTTP 302.

---

### GET /stats/{short_code}

Returns analytics for a short URL.

**Response `200 OK`:**

```json
{
  "short_code": "aB3xK9q",
  "long_url": "https://example.com/very/long/path",
  "click_count": 42,
  "created_at": "2026-05-18T12:00:00"
}
```

---

## Project Structure

```
scurto/
│
├── app/
│   ├── main.py          ← FastAPI app & all routes
│   ├── models.py        ← SQLAlchemy DB models
│   ├── schemas.py       ← Pydantic request/response shapes
│   ├── crud.py          ← All DB read/write operations
│   ├── database.py      ← Connection & session management
│   └── utils.py         ← Base62 encoder, UUID ID generator
│
├── static/
│   └── index.html       ← Full frontend UI (dark theme)
│
├── Dockerfile           ← Container config for Render
├── requirements.txt     ← Only 6 dependencies
└── README.md            ← You are here
```

## Run Locally

```bash
# Clone the repo
git clone https://github.com/aditya2027krml/scurto.git
cd scurto

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Create .env file
echo DATABASE_URL=sqlite:///./shortener.db > .env

# Run the server
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`

---

## Design Decisions & Trade-offs

**SQLite locally, PostgreSQL in production**  
SQLAlchemy abstracts the difference — swapping databases requires changing only one environment variable. No code changes.

**Synchronous FastAPI over async**  
For a CRUD-heavy application with simple DB lookups, synchronous handlers with connection pooling perform equally well and are significantly easier to debug and reason about.

**No Redis cache (yet)**  
At current scale, PostgreSQL with proper indexing on `short_code` (primary key) handles 100k+ reads/sec. Redis would be the next addition when read latency exceeds 10ms P99.

---

## What I'd add at scale

- **Redis cache** — cache-aside strategy, 24h TTL, >95% expected hit rate
- **Rate limiting** — token bucket per IP using Redis counters
- **Snowflake IDs** — replace UUID4 with time-ordered distributed IDs
- **Key-based sharding** — partition DB by `hash(short_code) % N` for 315B+ URLs
- **CDN layer** — push hot redirects to edge nodes for <1ms response
