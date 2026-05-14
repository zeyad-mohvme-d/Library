# 📚 Library Management System

A production-grade backend for **Project 2 — Library Management System**
(Backend Development with FastAPI course).

Built with **FastAPI · MySQL · Redis · JWT · Prometheus + Grafana · Docker · Pytest**.

> See [`CHAT.md`](./CHAT.md) for the full project log: requirement mapping, decisions, and build plan.

---

## ✨ Features

### Core (Library)
- CRUD for books (admin-only mutations, public reads)
- Borrow / return with availability validation
- Prevent borrowing unavailable books
- Per-user borrow limit (default **5**, configurable)
- Track borrow history per user (members) and globally (admins)

### Mandatory backend requirements
| Requirement | Status |
|---|---|
| Clean modular structure (routes / models / schemas / services) | ✅ `app/api/`, `app/models/`, `app/schemas/`, `app/services/` |
| Full RESTful CRUD with proper HTTP codes | ✅ 200 / 201 / 204 / 400 / 401 / 403 / 404 / 409 / 422 / 500 |
| Pydantic v2 validation + response models | ✅ all endpoints |
| JWT auth (register / login / token / verify / protect) | ✅ |
| RBAC (Admin Librarian + Member) | ✅ `require_admin`, `require_member` |
| Centralised error handling | ✅ `app/core/exceptions.py` |
| Redis caching (cache-aside + invalidation) | ✅ `app/core/cache.py` |
| Structured logging (loguru) — all log levels | ✅ `app/core/logging.py` |
| Monitoring dashboard (Prometheus + Grafana) | ✅ `monitoring/` |
| Pytest test suite (auth, RBAC, CRUD, business rules, edge cases) | ✅ 29 tests, all passing |

### Bonus
- ✅ **Docker** — `Dockerfile` + `docker-compose.yml` (full stack)
- ✅ **Frontend** — static HTML/CSS/JS UI in `frontend/`

---

## 🗂️ Project structure

```
Python&R_Project/
├── app/
│   ├── api/v1/          # auth.py, books.py, borrow.py
│   ├── core/            # config, security, deps, cache, logging, metrics, exceptions, middleware
│   ├── db/              # SQLAlchemy engine + session
│   ├── models/          # User, Book, BorrowRecord ORM
│   ├── schemas/         # Pydantic request/response models
│   ├── services/        # user_service, book_service, borrow_service
│   └── main.py          # FastAPI factory + lifespan
├── tests/               # pytest + TestClient (29 tests)
├── frontend/            # index.html, styles.css, app.js
├── monitoring/
│   ├── prometheus/      # prometheus.yml
│   └── grafana/         # auto-provisioned datasource + dashboard
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── pytest.ini
├── CHAT.md              # project log / decisions
└── README.md            # this file
```

---

## 🚀 Quick start

### Option A — Docker (recommended, full stack)

```bash
# 1. Clone & cd
git clone <your-repo-url> library-management-system
cd library-management-system

# 2. Start everything (API, MySQL, Redis, Prometheus, Grafana, Frontend)
docker compose up -d --build

# 3. Open the apps
# API docs (Swagger):  http://localhost:8000/docs
# API redoc:           http://localhost:8000/redoc
# Frontend:            http://localhost:8080
# Prometheus:          http://localhost:9090
# Grafana:             http://localhost:3000  (admin / admin)
# Metrics endpoint:    http://localhost:8000/metrics
```

The default admin (librarian) account is auto-seeded:

```
username: admin
password: Admin@12345
```

> **Important:** change `JWT_SECRET_KEY` and `DEFAULT_ADMIN_PASSWORD` in production.
> Generate a strong secret with `openssl rand -hex 32`.

### Option B — Local Python (no Docker)

```bash
# 1. Python 3.11+
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. Install
pip install -r requirements.txt

# 3. Configure env
cp .env.example .env
# Edit .env — point DATABASE_URL to your MySQL, REDIS_URL to your Redis,
# or set DATABASE_URL=sqlite:///./library.db for a fast local trial.

# 4. Run
uvicorn app.main:app --reload --port 8000
```

### Option C — Tests only (uses in-memory SQLite)

```bash
pip install -r requirements.txt
python -m pytest -v
```

Expected: **29 passed**.

---

## 🔌 API overview

All endpoints are versioned under `/api/v1`. Full interactive docs at `/docs`.

### Auth
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/auth/register` | — | Register a new member |
| POST | `/api/v1/auth/login`    | — | Login (form-encoded), returns JWT |
| GET  | `/api/v1/auth/me`       | Bearer | Current user info |

### Books (CRUD)
| Method | Path | Auth | Description |
|---|---|---|---|
| GET    | `/api/v1/books`         | — | List with pagination + search (cached) |
| GET    | `/api/v1/books/{id}`    | — | Get one (cached) |
| POST   | `/api/v1/books`         | Admin | Create |
| PUT    | `/api/v1/books/{id}`    | Admin | Update |
| DELETE | `/api/v1/books/{id}`    | Admin | Delete (returns 204) |

### Borrow / return
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/borrow`              | Bearer | Borrow a book |
| POST | `/api/v1/borrow/{id}/return`  | Bearer | Return (own record, or any if admin) |
| GET  | `/api/v1/borrow/me`           | Bearer | My borrow history |
| GET  | `/api/v1/borrow`              | Admin  | All borrow records (filterable) |

### Health & metrics
| Method | Path | Description |
|---|---|---|
| GET | `/`         | Service banner |
| GET | `/health`   | Liveness probe |
| GET | `/metrics`  | Prometheus exposition format |

---

## 🧠 Business rules

The service enforces these rules at the service layer (so they're tested too):
- A book cannot be borrowed if `available_copies == 0` → **422**
- A user cannot borrow the same book twice while still holding it → **422**
- A user cannot exceed `MAX_BORROW_PER_USER` simultaneous loans → **422**
- A user can only return their own loans (admins may return on behalf) → **403** otherwise
- Cannot return an already-returned record → **422**
- ISBN uniqueness enforced → **409** on duplicate
- `available_copies <= total_copies` enforced at DB level (CHECK constraint)

---

## 🪶 Caching (Redis, cache-aside)

- `GET /api/v1/books` and `GET /api/v1/books/{id}` are cached.
- TTL is `CACHE_TTL_SECONDS` (default 60s).
- **Invalidation:** every create/update/delete and every borrow/return wipes the `books:*` namespace.
- The cache **degrades gracefully** — if Redis is down, the API logs a warning and continues without caching.
- Custom Prometheus metric: `library_cache_events_total{event="hit|miss|invalidate"}`

To benchmark the speedup:

```bash
# Cold (cache miss)
time curl -s http://localhost:8000/api/v1/books > /dev/null
# Hot (cache hit)
time curl -s http://localhost:8000/api/v1/books > /dev/null
```

---

## 📊 Logging & monitoring

### Logging
- Library: **loguru**
- Levels used: DEBUG / INFO / WARNING / ERROR / CRITICAL
- Captures: incoming requests + response codes + latency, auth events, CRUD operations, validation errors, exceptions
- Outputs:
  - stdout (pretty in dev, JSON in prod)
  - rotating JSON file `logs/app.log` (10 MB, kept 14 days)

### Monitoring dashboard
Provisioned automatically. Open Grafana at <http://localhost:3000> (admin/admin) and find the dashboard **Library Management — Overview**:
- Total requests (5m)
- Error rate % (5m)
- Borrow success counter
- Cache hit ratio
- Request rate by status code
- Latency p50 / p95 / p99
- Auth attempts (login/register × success/failure)
- Borrow / return events over time

Custom metrics exported:
- `library_borrow_total{status="success|denied"}`
- `library_return_total`
- `library_auth_attempts_total{event,result}`
- `library_cache_events_total{event}`
- `library_db_query_seconds`

Plus all default request/latency histograms from `prometheus-fastapi-instrumentator`.

---

## 🧪 Testing

```bash
python -m pytest -v
```

29 tests covering:
- Authentication: register, login, duplicate handling, validation, wrong password, /me, invalid token, admin seeding
- Books CRUD: list, get, create (admin-only), update (admin-only), delete (admin-only), search, ISBN conflict
- Borrow / Return: happy path, unavailable book, double-borrow, borrow limit, others' record return, admin returns on behalf, my history, admin history requires admin
- Health: root, /health, /metrics, OpenAPI schema

Tests use an in-memory SQLite database with a `StaticPool` so multi-threaded `TestClient` calls share state. Redis is optional during tests — the cache layer auto-disables if unreachable.

---

## 🌳 Branching strategy (Git & GitHub)

```
main         (protected — only via reviewed PR)
└── develop  (integration branch)
    ├── feature/<member>/auth-jwt
    ├── feature/<member>/books-crud
    ├── feature/<member>/borrow-return
    ├── feature/<member>/caching-redis
    ├── feature/<member>/logging-monitoring
    ├── feature/<member>/testing
    ├── feature/<member>/frontend
    └── feature/<member>/docker
```

Each member owns at least one feature branch and opens a PR into `develop`.
After review, `develop` is merged into `main` for the final hand-in.

To bootstrap the repo:

```bash
git init
git checkout -b main
git add .
git commit -m "chore: initial scaffold"
git checkout -b develop
git remote add origin <your-github-url>
git push -u origin main develop
```

> ⚠️ The course penalises bulk/last-minute commits and single-author repos. Distribute the work and commit incrementally per feature.

---

## 👥 Team & roles

> Replace this section with your real team members and the area each person owned.

| Member | Role / Area |
|---|---|
| _Your Name_         | Project lead, JWT auth, RBAC |
| _Member 2_          | Books CRUD, schemas |
| _Member 3_          | Borrow/return business logic |
| _Member 4_          | Redis caching + invalidation |
| _Member 5_          | Logging, Prometheus, Grafana |
| _Member 6_          | Tests, frontend, Docker |

---

## 🔧 Configuration reference

All config is environment-driven via `pydantic-settings` (see `.env.example`). Key knobs:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `mysql+pymysql://...` | SQLAlchemy URL |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `JWT_SECRET_KEY` | _change-me_ | HMAC key for JWT |
| `JWT_ALGORITHM` | `HS256` | |
| `JWT_EXPIRE_MINUTES` | `60` | Access-token lifetime |
| `MAX_BORROW_PER_USER` | `5` | Per-user concurrent borrow limit |
| `DEFAULT_BORROW_DAYS` | `14` | Default loan period |
| `CACHE_TTL_SECONDS` | `60` | Redis cache TTL |
| `DEFAULT_ADMIN_USERNAME` | `admin` | Auto-seeded librarian |
| `DEFAULT_ADMIN_PASSWORD` | `Admin@12345` | Auto-seeded librarian password |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins |

---

## 📜 License

MIT (or as required by the course).
