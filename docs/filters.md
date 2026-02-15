The file `filters.py` centralizes filter application logic so the UI can stay simple and consistent across reruns.

It is designed to support an explicit **Apply Filters** button in the sidebar. This keeps filter selection and filter execution separate, which is clearer for non-technical users and avoids unexpected table changes while they are still selecting values.

### `apply_filters`

#### 1) Start from a copy of the data
We never mutate the original DataFrame. This keeps the base data intact and predictable.

```python
filtered = df.copy()
```

#### 2) Apply string filters
Each string filter has a default value of `"All"`. Only apply a filter when the user chooses a specific value.

```python
for col, val in st.session_state.filters_string.items():
    if val != "All":
        filtered = filtered[filtered[col] == val]
```

#### 3) Apply boolean filters
Boolean filters use the same `"All"` default to mean “no filtering”.

```python
for col, val in st.session_state.filters_boolean.items():
    if val != "All":
        filtered = filtered[filtered[col] == val]
```

#### 4) Apply timestamp filters
Timestamp filters use a `(min_date, max_date)` range, based on `column_tags`.  
If the selected range equals the default range, the filter is skipped.

```python
for col, value in st.session_state.filters_timestamp.items():
    if col not in filtered.columns:
        continue

    default_range = None
    if col in column_tags and "min_date" in column_tags[col] and "max_date" in column_tags[col]:
        default_range = (column_tags[col]["min_date"], column_tags[col]["max_date"])

    if default_range is not None and value == default_range:
        continue
```

#### 5) Parse and filter by date range
We only filter when there are valid values, and we compare on date-only values for consistency.

```python
series = filtered[col]
if series.isna().all():
    continue

parsed = pd.to_datetime(series, errors="coerce")
mask = parsed.notna() & (parsed.dt.date >= value[0]) & (parsed.dt.date <= value[1])
filtered = filtered[mask]
```

#### 6) Return the filtered result
The function returns the new filtered DataFrame, leaving the original untouched.

```python
return filtered
```

#### Why this matters
- Keeps filtering logic isolated from UI rendering.
- Makes it easier to add more filter types (boolean, timestamp, numeric) without changing the UI code.
- Enables explicit apply/reset actions in the sidebar.

### `reset_filters`

The reset behavior also lives in `filters.py` so the UI remains thin and consistent.

```python
def reset_filters(df: pd.DataFrame) -> None:
    st.session_state.filters_string = {
        c: "All"
        for c in df.select_dtypes(include=["string"]).columns
    }
    st.session_state.filters_boolean = {
        c: "All"
        for c in df.select_dtypes(include=["bool"]).columns
    }
    st.session_state.filters_timestamp = {
        col: (column_tags[col]["min_date"], column_tags[col]["max_date"])
        for col in column_tags
        if "min_date" in column_tags[col] and "max_date" in column_tags[col]
    }

    for col in st.session_state.filters_string:
        st.session_state[f"filter_{col}"] = "All"
    for col in st.session_state.filters_boolean:
        st.session_state[f"filter_bool_{col}"] = "All"
    for col, value in st.session_state.filters_timestamp.items():
        st.session_state[f"date_input_{col}"] = value

    st.session_state.filtered_df = df
```

Why this matters:
- Resets both the stored filter values and the widget state.
- Avoids stale UI selections after a reset.
- Keeps the table in sync with the default, unfiltered dataset.
- Reset is applied on the next rerun to avoid Streamlit widget state errors.
