The file `controllers/edits.py` contains helper functions for edit mode.  
Its purpose is to keep edit-related logic out of the UI so `app.py` stays simple.

### format_display_col

```python
def format_display_col(col_name: str) -> str:
    return " ".join(
        "ID" if word.lower() == "id" else word.capitalize()
        for word in col_name.split("_")
    )
```

What it does:
- Converts a snake_case column name (e.g., `item_id`) to the display format used in the UI (`Item ID`).
- Ensures the mapping matches `clean_column_names` in `models/shop_orders.py`.

Why it matters:
- The UI shows human-readable column names, but the business logic still needs to identify the primary key and lock columns accurately.

### normalize_pk / get_pk_display_cols / get_pk_db_cols

```python
def normalize_pk(pk_value) -> list[str]:
    return list(pk_value) if isinstance(pk_value, (list, tuple)) else [pk_value]

def get_pk_display_cols() -> list[str]:
    return [format_display_col(col) for col in normalize_pk(PRIMARY_KEY)]

def get_pk_db_cols() -> list[str]:
    return [display_to_db_col(col) for col in get_pk_display_cols()]
```

What they do:
- Support single or composite primary keys.
- Normalize `PRIMARY_KEY` into a list.
- Provide both display names (UI) and database names (Snowflake).

Why it matters:
- The app can work with tables that have multiple key columns without code changes.

### get_changed_rows

```python
def get_changed_rows(edited_df: pd.DataFrame, original_df: pd.DataFrame) -> pd.DataFrame:
    pk_cols = get_pk_display_cols()
    lock_col = format_display_col(LOCK_COL) if LOCK_COL else None

    if not all(col in edited_df.columns for col in pk_cols) or not all(
        col in original_df.columns for col in pk_cols
    ):
        return edited_df

    compare_cols = [
        c for c in edited_df.columns
        if c in original_df.columns and c not in pk_cols and c != lock_col
    ]

    edited_sub = edited_df.set_index(pk_cols)[compare_cols]
    original_sub = original_df.set_index(pk_cols)[compare_cols]
    original_sub = original_sub.loc[edited_sub.index]

    equal = edited_sub.eq(original_sub) | (edited_sub.isna() & original_sub.isna())
    changed_mask = ~equal.all(axis=1)
    return edited_df[changed_mask.values]
```

What it does:
- Builds a row-level diff between the edited DataFrame and the original snapshot.
- Excludes primary key columns and the lock column from comparisons.
- Returns only rows with actual changes.

Why it matters:
- Prevents unnecessary updates to unchanged rows.
- Produces accurate update counts.
- Reduces the workload of the Snowflake `MERGE`.

### build_change_log

```python
def build_change_log(edited_df: pd.DataFrame, original_df: pd.DataFrame) -> pd.DataFrame:
    pk_cols = get_pk_display_cols()
    pk_cols_db = get_pk_db_cols()
    lock_col = format_display_col(LOCK_COL) if LOCK_COL else None

    if not all(col in edited_df.columns for col in pk_cols) or not all(
        col in original_df.columns for col in pk_cols
    ):
        return pd.DataFrame(columns=pk_cols_db + ["COLUMN_NAME", "OLD_VALUE", "NEW_VALUE"])

    original_indexed = original_df.set_index(pk_cols)
    compare_cols = [c for c in edited_df.columns if c not in pk_cols and c != lock_col]
    rows = []

    for _, row in edited_df.iterrows():
        if len(pk_cols) == 1:
            row_key = row[pk_cols[0]]
        else:
            row_key = tuple(row[col] for col in pk_cols)

        if row_key not in original_indexed.index:
            continue
        original_row = original_indexed.loc[row_key]

        for col in compare_cols:
            new_val = row[col]
            old_val = original_row[col] if col in original_row.index else None

            if pd.isna(new_val) and pd.isna(old_val):
                continue
            if new_val == old_val:
                continue

            pk_payload = {db_col: row[disp_col] for disp_col, db_col in zip(pk_cols, pk_cols_db)}
            rows.append(
                {
                    **pk_payload,
                    "COLUMN_NAME": display_to_db_col(col),
                    "OLD_VALUE": old_val,
                    "NEW_VALUE": new_val,
                }
            )

    return pd.DataFrame(rows, columns=pk_cols_db + ["COLUMN_NAME", "OLD_VALUE", "NEW_VALUE"])
```

What it does:
- Builds a row-per-column change log.
- Stores all PK columns so pending approvals can identify the row.
- Keeps column names in database format for Snowflake inserts.

Why it matters:
- Composite keys are fully supported without losing traceability.

### Design Notes

- Edit logic is centralized here to keep `app.py` thin.
- Primary key and lock column names are always resolved from constants + display conversion.
- The functions are schema-agnostic and work with any table that follows the same PK/LOCK convention.
