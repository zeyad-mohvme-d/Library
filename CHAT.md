# Library Management System — Project Chat Log

> Conversation & decisions log for **Project 2: Library Management System**
> (Backend Development with FastAPI course)

---

## 1. Project Selection

From `Project_Instructions.pdf` (slide 5+), **Project 2: Library Management System** was chosen.

**Description:** Build a backend API for managing a library system with borrowing and tracking functionality.

**Entities**

- `Users`
- `Books`
- `BorrowRecords`

**Features**

- CRUD operations for books
- Borrow and return system with availability validation
- Prevent borrowing unavailable books
- Track borrowing history
- Limit number of borrowed books per user

**Roles**

- **Admin (Librarian)** — Manage books and view all records
- **Member** — Borrow, return, and view personal history

---

## 2. Mandatory Requirements (from PDF)

| # | Requirement | Where it lives in this project |
|---|---|---|
| 1 | Clean modular project structure (routes / models / schemas / services) | `app/api/`, `app/models/`, `app/schemas/`, `app/services/` |
| 2 | Full RESTful CRUD with proper HTTP codes, Pydantic validation, response models | `app/api/v1/*.py` + `app/schemas/*.py` |
| 3 | JWT authentication (register / login / token gen / token validation / protected routes) | `app/api/v1/auth.py`, `app/core/security.py`, `app/core/deps.py` |
| 4 | Role-based authorization (Admin vs Member) | `app/core/deps.py` (`require_admin`, `require_member`) |
| 5 | Error handling (HTTPException, validation errors, descriptive messages) | `app/core/exceptions.py`, FastAPI exception handlers |
| 6 | Git & GitHub with branches & per-member commits | `.git/`, `README.md` (branching strategy doc) |
| 7 | Redis caching (cache-aside, invalidation, perf improvement) | `app/core/cache.py`, used in `app/services/book_service.py` |
| 8 | Logging (loguru, all levels) + Monitoring dashboard (Prometheus + Grafana) | `app/core/logging.py`, `app/core/metrics.py`, `monitoring/` |
| 9 | API testing with pytest + TestClient | `tests/` |

## 3. Bonus (extra points, included)

- **Frontend** — `frontend/` (HTML/CSS/JS, talks to FastAPI)
- **Docker** — `Dockerfile`, `docker-compose.yml` (API + MySQL + Redis + Prometheus + Grafana)

---

## 4. Tech-stack decisions

| Concern | Choice | Why |
|---|---|---|
| Framework | **FastAPI** | Async, auto OpenAPI, native Pydantic validation — strongest fit for the rubric |
| ORM | **SQLAlchemy 2.x** | Standard with FastAPI, clean session handling |
| DB | **MySQL 8** | User preference |
| Auth | **JWT** (`python-jose`) + **bcrypt** (`passlib`) | Required + safe |
| Cache | **Redis 7** | Required by rubric |
| Logging | **loguru** | Cleaner than stdlib logging, structured JSON logs |
| Metrics | **prometheus-fastapi-instrumentator** | Auto-exports request count, latency, error rate |
| Dashboard | **Grafana** with prebuilt JSON | Required dashboard + nice to demo |
| Tests | **pytest** + FastAPI **TestClient** + SQLite (in-memory) | Required; SQLite for fast isolated tests |
| Frontend | Vanilla **HTML / CSS / JS** | Smallest cognitive overhead, demonstrates API integration |
| Container | **Docker** + **docker-compose** | Bonus, full stack in one command |

---

## 5. Branching strategy (recommended for the team)

```
main         <-- protected, only via PR after review
└── develop  <-- integration branch, all features merge here
    ├── feature/<member>/auth-jwt
    ├── feature/<member>/books-crud
    ├── feature/<member>/borrow-return
    ├── feature/<member>/caching-redis
    ├── feature/<member>/logging-monitoring
    ├── feature/<member>/testing
    ├── feature/<member>/frontend
    └── feature/<member>/docker
```

Each member should own at least one feature branch and open a PR into `develop`. After review, `develop` is merged into `main` for the final hand-in.

> Penalty risk noted in PDF: bulk/last-minute commits or commits from a single member are penalized. Distribute the work across the team.

---

## 6. Build plan (this conversation)

1. Create this `CHAT.md` ✅
2. Scaffold the FastAPI project tree
3. Database layer (User, Book, BorrowRecord) with constraints
4. JWT auth + RBAC
5. Books CRUD
6. Borrow / Return system
7. Redis caching (cache-aside + invalidation)
8. Logging (loguru) + Prometheus metrics + Grafana dashboard
9. Pytest test suite
10. Vanilla HTML/JS frontend
11. Dockerfile + docker-compose
12. README.md with full run instructions
13. Verify by installing deps and running pytest

---

## 7. Notes & guardrails

- Project instructions state that any non-compliance with mandatory requirements is a violation — this scaffold covers every numbered point.
- Borrow limit defaults to **5** per user (configurable via env).
- Default Admin (librarian) is auto-seeded on first boot — credentials in `.env.example`.
- All passwords stored bcrypt-hashed; tokens HS256 signed.
- Every state-changing endpoint invalidates relevant cache keys.
- Logs are JSON-structured so Grafana / any log shipper can parse them.

---

_Last updated automatically as the project was built._
