---
name: repositories
description: "Skill for the Repositories area of dealtracker. 11 symbols across 4 files."
---

# Repositories

11 symbols | 4 files | Cohesion: 100%

## When to Use

- Working with code in `backend/`
- Understanding how create_deal, update_deal, dashboard_kpis work
- Modifying repositories-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `backend/app/repositories/in_memory.py` | _utc_now, __init__, _seed, create_deal, update_deal (+3) |
| `backend/app/api/routes/dashboard.py` | get_kpis |
| `backend/app/api/routes/settings.py` | list_user_mappings |
| `backend/app/api/routes/twilio.py` | receive_twilio_webhook |

## Entry Points

Start here when exploring this area:

- **`create_deal`** (Function) — `backend/app/repositories/in_memory.py:52`
- **`update_deal`** (Function) — `backend/app/repositories/in_memory.py:62`
- **`dashboard_kpis`** (Function) — `backend/app/repositories/in_memory.py:73`
- **`get_kpis`** (Function) — `backend/app/api/routes/dashboard.py:9`
- **`list_users`** (Function) — `backend/app/repositories/in_memory.py:80`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `create_deal` | Function | `backend/app/repositories/in_memory.py` | 52 |
| `update_deal` | Function | `backend/app/repositories/in_memory.py` | 62 |
| `dashboard_kpis` | Function | `backend/app/repositories/in_memory.py` | 73 |
| `get_kpis` | Function | `backend/app/api/routes/dashboard.py` | 9 |
| `list_users` | Function | `backend/app/repositories/in_memory.py` | 80 |
| `list_user_mappings` | Function | `backend/app/api/routes/settings.py` | 9 |
| `find_user_by_whatsapp` | Function | `backend/app/repositories/in_memory.py` | 91 |
| `receive_twilio_webhook` | Function | `backend/app/api/routes/twilio.py` | 8 |
| `_utc_now` | Function | `backend/app/repositories/in_memory.py` | 8 |
| `__init__` | Function | `backend/app/repositories/in_memory.py` | 13 |
| `_seed` | Function | `backend/app/repositories/in_memory.py` | 18 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `__init__ → _utc_now` | intra_community | 3 |

## How to Explore

1. `gitnexus_context({name: "create_deal"})` — see callers and callees
2. `gitnexus_query({query: "repositories"})` — find related execution flows
3. Read key files listed above for implementation details
