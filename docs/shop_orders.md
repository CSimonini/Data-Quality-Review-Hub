# `models/shop_orders.py`

This module contains data access and write-back logic for Snowflake.

Main responsibilities:
1. Create the Snowpark session.
2. Load and normalize table data.
3. Infer and tag date/timestamp fields.
4. Validate edits against Snowflake schema limits.
5. Merge valid changes into the base table.
6. Log approved-pending rows into the pending queue.

## Session Setup

The module builds a Snowpark session from `st.secrets`.

Why it matters:
- Keeps DB connectivity centralized in one module.
- Reused by load, merge, and log functions.

## `clean_column_names(df)`

Converts DB-style names (snake_case) to UI-friendly names.

Example:
- `order_id` -> `Order ID`
- `order_line_number` -> `Order Line Number`

This aligns display labels with non-technical user expectations.

## `auto_convert_dtypes(df)` + `column_tags`

The function:
- runs `convert_dtypes()`
- tries datetime parsing with explicit formats
- converts date-only timestamps to `datetime.date`
- stores per-column tags in `column_tags`

`column_tags` stores:
- semantic type (`date` / `timestamp`)
- `min_date` / `max_date` for filter defaults

This supports dynamic and schema-agnostic filter generation.

## `load_data()`

```python
@st.cache_data(ttl=60)
def load_data() -> pd.DataFrame:
    order_clause = f" ORDER BY {ORDER_BY}" if ORDER_BY else ""
    df = session.sql(f"""
        SELECT *
        FROM {DATABASE}.{SCHEMA}.{TABLE}{order_clause}
    """).to_pandas()
    ...
```

Behavior:
- reads `DATABASE`, `SCHEMA`, `TABLE`, `ORDER_BY` from constants
- cleans names
- applies dtype inference

`ORDER_BY` is optional.

## Schema Metadata + Validation

### `get_table_schema_metadata()`

Reads column metadata from:
- `{DATABASE}.information_schema.columns`

Includes:
- `DATA_TYPE`
- `CHARACTER_MAXIMUM_LENGTH`
- `NUMERIC_PRECISION`
- `NUMERIC_SCALE`

### `validate_changes_against_schema(changes_df)`

Runs before merge and returns a list of validation errors.

Current checks:
- `VARCHAR(n)`: blocks strings longer than `n`
- `NUMBER(p,s)`: blocks values exceeding precision/scale

Why it matters:
- Prevents Snowflake DML errors before write-back.
- Produces user-friendly error messages in UI.

## `merge_changes(changes_df)`

This function updates the base table.

Flow:
1. normalize DataFrame index (`reset_index(drop=True)`)
2. normalize column names to DB format
3. write changed rows to temp stage table: `STREAMLIT_TABLE_BASE_CHANGES`
4. build dynamic `MERGE` using all PK columns
5. update non-key columns (+ `LOCK_COL` timestamp when configured)

Notes:
- supports composite primary keys (`PRIMARY_KEY` string or list)
- uses `table_type="temp"` for merge stage

## Pending Queue Tables

The module uses two pending-related tables:

- `PENDING_STAGE_TABLE`: temporary technical stage
- `PENDING_TABLE`: persistent approval queue

### `ensure_pending_table_exists(pk_cols_db)`

Creates `PENDING_TABLE` on demand (if missing) with:
- PK columns (as `VARCHAR`)
- `column_name`
- `old_value` / `new_value` as `VARIANT`
- `changed_by`
- `changed_at` default timestamp
- `approval_status` default `PENDING`

### `log_pending_changes(change_log_df)`

Flow:
1. normalize index (`reset_index(drop=True)`)
2. write `change_log_df` to `PENDING_STAGE_TABLE` (`temp`)
3. ensure persistent `PENDING_TABLE` exists
4. insert from stage to pending queue
5. set `changed_by` with `current_user()`

Important:
- this function logs change rows, not full table rows
- it is called after successful merge in `app.py`

## Design Intent

- Keep write-back robust but schema-agnostic.
- Prevent type-range errors early.
- Preserve an auditable pending queue for future approval workflows.
