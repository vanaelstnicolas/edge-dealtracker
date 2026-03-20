# DealTracker Backend (FastAPI)

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API base URL: `http://127.0.0.1:8000/api`

## Implemented endpoints

- `GET /health`
- `GET /deals`
- `POST /deals`
- `PATCH /deals/{deal_id}`
- `GET /dashboard/kpis`
- `GET /settings/users`
- `PUT /settings/users/{user_id}`
- `POST /webhooks/twilio`
