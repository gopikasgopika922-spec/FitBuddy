# FitBuddy — AI Fitness Plan Generator

FitBuddy is a FastAPI + Jinja2 + SQLite web application that generates personalized 7-day workout plans, nutrition/recovery tips, and feedback-based plan revisions with Google Gemini.

## What is included

- FastAPI backend and HTML/Jinja2 frontend
- SQLite + SQLAlchemy persistence
- Gemini integration using Google's current `google-genai` Python SDK
- Configurable workout and nutrition models
- Demo mode so the complete app can run without an API key
- Feedback-based plan regeneration
- Protected admin dashboard
- JSON API endpoints plus browser pages
- Automated tests
- Responsive CSS UI
- `.env` configuration and `.gitignore`

The original project documentation describes Gemini 1.5 Pro and Gemini Flash. Those model names are historical. This implementation keeps the documented architecture—one stronger model for workout generation/revision and a fast model for nutrition—while making the model IDs configurable. The default model IDs are current Gemini models and can be changed in `.env`.

## Requirements

- Python 3.11+
- pip
- A Gemini API key for real AI generation
- VS Code recommended

## Quick start — Windows PowerShell

```powershell
cd FitBuddy
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Open `.env` and set:

```env
GEMINI_API_KEY=your_real_key_here
DEMO_MODE=false
```

Then:

```powershell
uvicorn app.main:app --reload
```

Open:

- http://127.0.0.1:8000
- http://127.0.0.1:8000/docs
- http://127.0.0.1:8000/view-all-users

Admin dashboard credentials are controlled by:

```env
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change-me
```

## Quick start — macOS/Linux

```bash
cd FitBuddy
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

## Demo mode

To test the complete application without calling Gemini:

```env
DEMO_MODE=true
```

Demo mode generates deterministic sample workout plans and nutrition tips. This is useful for checking the UI, database, routes, and tests before adding an API key.

## API

### Generate a plan

`POST /api/generate`

JSON body:

```json
{
  "username": "Alex",
  "user_id": "alex-001",
  "age": 28,
  "weight": 72,
  "goal": "muscle gain",
  "intensity": "medium"
}
```

### Update a plan

`POST /api/feedback`

```json
{
  "user_id": "alex-001",
  "feedback": "Add more cardio and one additional rest day."
}
```

### Health

`GET /api/health`

### User lookup

`GET /api/users/{user_id}`

### Admin user list

`GET /api/users` requires HTTP Basic authentication using the configured admin credentials.

## Project structure

```text
FitBuddy/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── database.py
│   ├── gemini_service.py
│   ├── main.py
│   ├── models.py
│   ├── routes.py
│   └── schemas.py
├── static/
│   └── css/
│       └── style.css
├── templates/
│   ├── all_users.html
│   ├── base.html
│   ├── index.html
│   └── result.html
├── tests/
│   ├── conftest.py
│   └── test_app.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Testing

With the virtual environment active:

```bash
pytest -q
```

The test suite forces demo mode and uses a temporary SQLite database, so it does not require Gemini.

## Notes

- Fitness plans are general wellness content, not medical advice.
- Do not use generated plans as a substitute for professional medical or fitness guidance where appropriate.
- For production deployment, add real authentication/authorization, CSRF protection for browser forms, rate limiting, HTTPS, encrypted secrets, database migrations, and proper logging/monitoring.
