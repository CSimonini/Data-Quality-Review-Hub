# Snowflake Data Review and Edit Console

Production-quality Streamlit app for data review, controlled editing, and Snowflake write-back.

## What it does

- Loads data from Snowflake (Snowpark).
- Normalizes column names for business users.
- Infers data types and builds dynamic filters.
- Supports explicit Apply/Reset filter workflow.
- Lets users edit rows in a controlled editor.
- Merges only changed rows into the base table.
- Logs field-level changes into a pending approval queue.

## Key behaviors

- Schema-agnostic loading through constants (`DATABASE`, `SCHEMA`, `TABLE`, `ORDER_BY`).
- Composite PK support (`PRIMARY_KEY` can be a string or a list).
- PK and lock columns are read-only in the editor.
- Save flow validates edits against Snowflake limits before write-back:
  - `VARCHAR(n)` length checks
  - `NUMBER(p,s)` precision/scale checks
- Write-back order is:
  1. Merge base-table changes
  2. Log pending changes

This prevents pending rows from being stored if merge fails.

## Pending tables

- `PENDING_STAGE_TABLE`: temporary technical stage table.
- `PENDING_TABLE`: persistent queue for approval workflow.

If `PENDING_TABLE` does not exist, the app creates it automatically on first save.

## Main files

- `app.py`: UI orchestration, editor mode, save flow, messages.
- `models/shop_orders.py`: loading, type inference, validation, merge, pending log.
- `controllers/filters.py`: filter application and reset.
- `controllers/edits.py`: change detection and change-log build.
- `init_state.py`: session state bootstrap and data refresh.
- `constants.py`: runtime configuration.

## Run

```bash
streamlit run app.py
```

## Docs

Detailed docs are in `docs/`.


