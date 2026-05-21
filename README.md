# QuboolMatch

A full-stack matching platform that connects people through an intelligent interest-based system with profile visibility controls and mutual match limits.

## What It Does

QuboolMatch is a web application where users can browse profiles, send interest requests to people they like, and establish mutual connections. Once both users accept each other's interests, they can view full profiles. The system limits users to 3 mutual matches to encourage quality connections over quantity.

## Tech Stack

**Frontend:** TypeScript (59.8%), React, Vite, HTML/CSS

**Backend:** Python (39%), FastAPI, PostgreSQL, SQLAlchemy, Pydantic, JWT Authentication

**Infrastructure:** Docker, Docker Compose, Uvicorn

## Key Features

- User registration and JWT-based authentication
- Browse users with filters (location, religion, age, profession)
- Send/receive/accept/reject interest requests
- Real-time notifications for interest events
- Two-tier profile visibility: brief (public) and full (mutual matches only)
- 3-mutual-match limit per user
- Notification management (read, delete, mark all as read)

## Project Structure

```
QuboolMatch/
├── frontend/          # React TypeScript UI
├── backend/           # FastAPI Python backend
├── docker-compose.yml # Service orchestration
└── Documentation/     # Setup & implementation guides
```

## Quick Start

### With Docker
```bash
git clone https://github.com/Tajkia03/QuboolMatch.git
cd QuboolMatch
cp .env.example .env
docker compose up -d
```

### Manual Setup
```bash
# Backend
cd backend && python -m venv venv
source venv/bin/activate && pip install -r requirements.txt
uvicorn main:app --reload

# Frontend (new terminal)
cd frontend && npm install && npm run dev
```

## API Endpoints

**Interests:** POST/GET /api/interests/{send, received, sent, matches}, PUT /api/interests/{id}/{accept, reject}

**Notifications:** GET /api/notifications, PUT /api/notifications/{id}/{read, read-all}, DELETE /api/notifications/{id}

**Users:** GET /api/users/browse, GET /api/users/{id}/profile/full, POST/POST /auth/{sign_up, sign_in}

## Database Tables

- **users** - Account info, profiles, preferences
- **interests** - Interest requests (from_user_id, to_user_id, status: pending/accepted/rejected)
- **notifications** - Alerts (type: interest_received/accepted/rejected, is_read status)

## Business Rules

- Users can send interests to people within 3-mutual-match limit
- Brief profiles visible to all; full profiles only to mutual matches
- Rejected/pending interests don't count toward the 3-match limit
- Notifications auto-created for: interest_received, interest_accepted, interest_rejected

## Access

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Database: localhost:5434

## Testing

1. Create 2+ accounts
2. Login as User 1 → Browse users → Send interest
3. Login as User 2 → See notification → Accept interest
4. Both users now see mutual match status
5. Try sending 4th interest after having 3 matches → Verify limit enforcement

## Documentation

- **QUICK_START.md** - Setup and testing guide
- **IMPLEMENTATION_SUMMARY.md** - Technical details and endpoints
- **FRONTEND_INTEGRATION_GUIDE.md** - Frontend implementation
- **TESTING_CHECKLIST.md** - Comprehensive test scenarios

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Backend won't start | Check PostgreSQL is running, verify .env credentials |
| Frontend shows errors | Ensure backend runs on http://localhost:8000, check browser console |
| Docker issues | Run `docker compose logs backend` to debug, rebuild with `--no-cache` |

---

**Made by students | TypeScript (60%) + Python (39%) | Full-stack matching application**
