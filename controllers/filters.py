import streamlit as st
import pandas as pd

from models.shop_orders import column_tags

def apply_filters(df: pd.DataFrame) -> pd.DataFrame:

    filtered = df.copy()

    for col, val in st.session_state.filters_string.items():
        if val != "All":
            filtered = filtered[filtered[col] == val]

    for col, val in st.session_state.filters_boolean.items():
        if val != "All":
            filtered = filtered[filtered[col] == val]

    for col, value in st.session_state.filters_timestamp.items():
        if col not in filtered.columns:
            continue

        default_range = None
        if col in column_tags and "min_date" in column_tags[col] and "max_date" in column_tags[col]:
            default_range = (column_tags[col]["min_date"], column_tags[col]["max_date"])

        if default_range is not None and value == default_range:
            continue

        series = filtered[col]
        if series.isna().all():
            continue

        parsed = pd.to_datetime(series, errors="coerce")
        mask = parsed.notna() & (parsed.dt.date >= value[0]) & (parsed.dt.date <= value[1])
        filtered = filtered[mask]

    return filtered

def reset_filters(df: pd.DataFrame) -> None:
    # Restore defaults for all filter types
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

    # Reset widget state so the sidebar reflects defaults immediately
    for col in st.session_state.filters_string:
        st.session_state[f"filter_{col}"] = "All"
    for col in st.session_state.filters_boolean:
        st.session_state[f"filter_bool_{col}"] = "All"
    for col, value in st.session_state.filters_timestamp.items():
        st.session_state[f"date_input_{col}"] = value

    # Clear any filtered view
    st.session_state.filtered_df = df
