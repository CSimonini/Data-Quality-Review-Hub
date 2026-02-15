The file `app.py` is the main Streamlit entry point.

It does five things:
1. Initializes app state.
2. Renders staged filters in the sidebar.
3. Shows table or editor mode.
4. Validates edits before write-back.
5. Executes write-back with clear user feedback.

## Imports

```python
from init_state import init_state, refresh_data
from controllers.filters import apply_filters, reset_filters
from controllers.edits import get_changed_rows, format_display_col, build_change_log, get_pk_display_cols
from constants import MAX_ROWS, PRIMARY_KEY, LOCK_COL
from models.shop_orders import (
    column_tags,
    merge_changes,
    log_pending_changes,
    validate_changes_against_schema,
)
```

Why this matters:
- UI logic stays in `app.py`.
- Filtering and edit diff logic stay in controllers.
- Data write-back and schema validation stay in the model.

## State Initialization

```python
init_state()
```

This ensures `df`, filters, and edit state always exist on rerun.

## Write-back Logger

`app.py` sets a logger that writes both to:
- `logs/write_back.log`
- terminal output

This gives users a generic error message while keeping technical details for debugging.

## Sidebar Filters (staged apply)

The sidebar builds filters in the same order as table columns.

Selections are staged in local dicts:
- `new_filters_string`
- `new_filters_boolean`
- `new_filters_timestamp`

Filters are committed only on **Apply Filters**:

```python
st.session_state.filters_string = new_filters_string
st.session_state.filters_boolean = new_filters_boolean
st.session_state.filters_timestamp = new_filters_timestamp
st.session_state.filtered_df = apply_filters(st.session_state.df)
```

Reset uses `reset_filters_pending` and reruns before widget creation to avoid Streamlit key/state conflicts.

## Data Display + Edit Mode

The app displays:
- `st.dataframe` when not editing
- `st.data_editor` when editing

The editor disables:
- all primary key columns (`get_pk_display_cols()`)
- `LOCK_COL` (if configured)

## Overflow-safe Editor Handling

`st.data_editor` is wrapped in `try/except OverflowError`.

If a user inputs a value too large for a numeric pandas dtype, the app:
- clears editor state (`main_data_editor` key)
- shows a friendly error
- avoids a full app crash loop

## Save Flow (current order)

On **Save Changes**:
1. `get_changed_rows(...)`
2. `validate_changes_against_schema(changes_df)`
3. `build_change_log(...)`
4. `merge_changes(changes_df)`
5. `log_pending_changes(change_log_df)`
6. `refresh_data()`

Important:
- Validation runs before merge.
- Pending log runs only after a successful merge.
- This avoids writing approval-log rows for failed base-table updates.

## Validation Behavior

When validation fails, app shows:
- `Validation failed...`
- one line per failing field

Examples:
- string too long for `VARCHAR(n)`
- value exceeds `NUMBER(p,s)` precision/scale

## User Feedback

- No changes: `st.info("No changes detected.")`
- Success: `st.success(...)` then rerun
- Failure: user-friendly error + technical log entry

## Why this structure

- Predictable UX for non-technical users.
- Strong type safety before write-back.
- Separation of concerns between UI, filtering, diffing, and database operations.
- Schema-agnostic behavior driven by constants and runtime metadata.
