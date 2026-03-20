---
name: schemas
description: "Skill for the Schemas area of dealtracker. 3 symbols across 1 files."
---

# Schemas

3 symbols | 1 files | Cohesion: 100%

## When to Use

- Working with code in `backend/`
- Understanding how DealBase, DealCreate, DealRead work
- Modifying schemas-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `backend/app/schemas/deal.py` | DealBase, DealCreate, DealRead |

## Entry Points

Start here when exploring this area:

- **`DealBase`** (Class) — `backend/app/schemas/deal.py:13`
- **`DealCreate`** (Class) — `backend/app/schemas/deal.py:22`
- **`DealRead`** (Class) — `backend/app/schemas/deal.py:34`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `DealBase` | Class | `backend/app/schemas/deal.py` | 13 |
| `DealCreate` | Class | `backend/app/schemas/deal.py` | 22 |
| `DealRead` | Class | `backend/app/schemas/deal.py` | 34 |

## How to Explore

1. `gitnexus_context({name: "DealBase"})` — see callers and callees
2. `gitnexus_query({query: "schemas"})` — find related execution flows
3. Read key files listed above for implementation details
