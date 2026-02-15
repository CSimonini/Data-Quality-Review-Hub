import streamlit as st
from models.shop_orders import load_data, column_tags

def init_state():
    if "df" not in st.session_state:
        # Load once per session to avoid repeated Snowflake queries
        st.session_state.df = load_data()

    # deep=True ensures true immutability for change tracking
    if "original_df" not in st.session_state:
        st.session_state.original_df = st.session_state.df.copy(deep=True)

    if "edit_mode" not in st.session_state:
        st.session_state.edit_mode = False

    if "filters_string" not in st.session_state:
        # Default to "All" so the dataset is unfiltered on first load
        st.session_state.filters_string = {
            c: "All"
            for c in st.session_state.df.select_dtypes(include=["string"]).columns
        }

    if "filters_boolean" not in st.session_state:
        # Boolean filters use the same "All" neutral default
        st.session_state.filters_boolean = {
            c: "All"
            for c in st.session_state.df.select_dtypes(include=["bool"]).columns
        }

    if 'filters_timestamp' not in st.session_state:
        st.session_state.filters_timestamp = {
            col: (column_tags[col]["min_date"], column_tags[col]["max_date"]) for col in column_tags
        }

def refresh_data():
    # Clear cached load_data and refresh the session DataFrame
    st.cache_data.clear()
    st.session_state.df = load_data()
    st.session_state.filtered_df = st.session_state.df
    st.session_state.reset_filters_pending = True

new_filters_string = {}
new_filters_boolean = {}
new_filters_timestamp = {}
