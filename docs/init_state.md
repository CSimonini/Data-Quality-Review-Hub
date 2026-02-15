The file `init_state.py` initializes and manages Streamlit `session_state`, which is the persistent memory of the app during a user session. Streamlit reruns the script on every interaction, so anything not stored in `session_state` is lost between reruns.

`session_state` keeps the UI consistent, avoids unnecessary reloads from Snowflake, and allows filters and edits to persist.

### DataFrame Initialization

```python
if "df" not in st.session_state:
    st.session_state.df = load_data()
```

`st.session_state.df` is the core dataset. It is loaded once from `load_data()` in `models.shop_orders` and reused across interactions.

Why this matters:
- Prevents repeated Snowflake calls on every rerun.
- Enables incremental filtering and editing.
- Keeps the application responsive for non-technical users.

### Edit State Initialization

```python
if "original_df" not in st.session_state:
    st.session_state.original_df = st.session_state.df.copy(deep=True)

if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = False
```

Why this matters:
- `original_df` provides a clean snapshot when entering edit mode.
- `edit_mode` controls whether the UI shows `dataframe` or `data_editor`.
- `deep=True` makes a full copy so later edits to `df` don't mutate the snapshot.

### Filter Initialization

The filters are built dynamically from the DataFrame schema. This is required for schema-agnostic behavior.

#### String Filters
```python
if "filters_string" not in st.session_state:
    st.session_state.filters_string = {
        c: "All"
        for c in st.session_state.df.select_dtypes(include=["string"]).columns
    }
```

Each string column receives a default value of `"All"` so the full dataset remains visible until a user selects a specific value.

Example:
```json
{
  "Customer Name": "All",
  "Customer Address": "All",
  "Customer Nation": "All"
}
```

#### Boolean Filters
```python
if "filters_boolean" not in st.session_state:
    st.session_state.filters_boolean = {
        c: "All"
        for c in st.session_state.df.select_dtypes(include=["bool"]).columns
    }
```

Boolean filters use the same `"All"` default so the dataset is unchanged until a user chooses `True` or `False`.

#### Timestamp Filters
```python
if "filters_timestamp" not in st.session_state:
    st.session_state.filters_timestamp = {
        col: (column_tags[col]["min_date"], column_tags[col]["max_date"])
        for col in column_tags
    }
```

Timestamp filters use `column_tags` (built during `auto_convert_dtypes`) to define a default date range for each timestamp column. This avoids relying on Pandas `object` dtypes and ensures the UI receives valid bounds.

Why this matters:
- The app uses `st.date_input` in range mode, which expects a `(start_date, end_date)` tuple.
- Storing the range in `session_state` ensures the widget always has a valid default on reruns.

### Schema-Agnostic Behavior

All filter dictionaries are built at runtime by inspecting the DataFrame and `column_tags`. This design:
- Avoids hardcoding column names or types.
- Keeps filters aligned with the current dataset schema.
- Preserves type safety and data integrity.

### Staging Dictionaries (Apply Button)

```python
new_filters_string = {}
new_filters_boolean = {}
new_filters_timestamp = {}
```

These dictionaries are used as **staging buffers** when the UI includes an **Apply Filters** button. The idea is:
- Users can change filter widgets without immediately changing `session_state`.
- Only when they click **Apply** do the staged values get committed.
- This makes the UI more predictable and avoids accidental filtering during selection.

If you stage filters locally inside `app.py`, these module-level dictionaries can be removed to avoid confusion.

### Data Refresh Helper

```python
def refresh_data():
    st.cache_data.clear()
    st.session_state.df = load_data()
    st.session_state.filtered_df = st.session_state.df
    st.session_state.reset_filters_pending = True
```

This helper is used after write-back to Snowflake. It clears the cached `load_data()` result and reloads the current table so the UI reflects the latest changes.
It also schedules a filter reset on the next rerun to keep the sidebar state consistent.
