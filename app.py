import streamlit as st
import pandas as pd
import time
import logging
import os

from init_state import init_state, refresh_data
from controllers.filters import apply_filters, reset_filters
from controllers.edits import get_changed_rows, format_display_col, build_change_log, get_pk_display_cols
from constants import MAX_ROWS, PRIMARY_KEY, LOCK_COL
from models.shop_orders import column_tags, merge_changes, log_pending_changes, validate_changes_against_schema

# --------------------------------------------------
# Init session state
# --------------------------------------------------

# st.logo(name.svg)
init_state()

# Write-back logging (file + console)
logger = logging.getLogger("write_back")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    os.makedirs("logs", exist_ok=True)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

    file_handler = logging.FileHandler(os.path.join("logs", "write_back.log"))
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

# Staged filters are local to this run to avoid mutating session state
new_filters_string = {}
new_filters_boolean = {}
new_filters_timestamp = {}

# Handle reset before widgets are instantiated to avoid Streamlit state errors
if st.session_state.get("reset_filters_pending"):
    reset_filters(st.session_state.df)
    st.session_state.reset_filters_pending = False

# --------------------------------------------------
# Sidebar Filters
# --------------------------------------------------
st.sidebar.header("Filters")

# Build filter widgets in the same order as the table columns
ordered_cols = list(st.session_state.df.columns)

# Build filter widgets in the same order as the table columns
for col in ordered_cols:
    if col in st.session_state.filters_string:
        options = ["All"] + sorted(
            st.session_state.df[col].dropna().unique().tolist()
        )

        selected_value = st.sidebar.selectbox(
            label=col,
            options=options,
            index=options.index(st.session_state.filters_string[col]),
            key=f"filter_{col}"
        )

        # Stage selected values so filters only apply on button click
        new_filters_string[col] = selected_value
        continue

    if col in st.session_state.filters_boolean:
        options = ["All", True, False]

        selected_value = st.sidebar.selectbox(
            label=col,
            options=options,
            index=options.index(st.session_state.filters_boolean[col]),
            key=f"filter_bool_{col}"
        )
        new_filters_boolean[col] = selected_value
        continue

    if col in st.session_state.filters_timestamp:
        # Skip columns that are missing tag metadata
        if col not in column_tags:
            continue

        # Use stable bounds so users can expand/shrink the range freely
        default_range = (column_tags[col]["min_date"], column_tags[col]["max_date"])

        # Normalize stored values in case a single date was saved
        current_value = st.session_state.filters_timestamp.get(col, default_range)
        if not isinstance(current_value, tuple) or len(current_value) != 2:
            current_value = (current_value, current_value)

        date_input_key = f"date_input_{col}"
        date_input_kwargs = {
            "label": f"{col}",
            "min_value": default_range[0],
            "max_value": default_range[1],
            "format": "MM.DD.YYYY",
            "key": date_input_key,
        }
        if date_input_key not in st.session_state:
            date_input_kwargs["value"] = current_value

        selected_value = st.sidebar.date_input(**date_input_kwargs)
        new_filters_timestamp[col] = selected_value

# ----------------- Buttons in the Sidebar -----------------

with st.sidebar.container(key="filter_buttons"):

    button_cols = st.columns(2)
    
    if button_cols[0].button("Apply Filters", key="apply_filters_button_id"):
        # Commit staged filters and compute a filtered view
        st.session_state.filters_string = new_filters_string
        st.session_state.filters_boolean = new_filters_boolean
        st.session_state.filters_timestamp = new_filters_timestamp
        st.session_state.filtered_df = apply_filters(st.session_state.df)
        st.rerun() # Rerun to apply filters and update button state

    if button_cols[1].button("Reset Filters", key="reset_filters_button_id"):
        st.session_state.reset_filters_pending = True
        st.rerun()

# --------------------------------------------------
# Display DataFrame
# --------------------------------------------------
# Show the filtered view when available, otherwise fall back to the base data
df_to_show = st.session_state.get("filtered_df", st.session_state.df).head(MAX_ROWS).reset_index(drop=True)

if st.session_state.edit_mode:
    pk_cols = get_pk_display_cols()
    lock_col = format_display_col(LOCK_COL) if LOCK_COL else None
    editor_key = "main_data_editor"

    try:
        edited_df = st.data_editor(
            df_to_show,
            hide_index=True,
            use_container_width=True,
            height=400,
            key=editor_key,
            disabled=pk_cols + ([lock_col] if lock_col else [])
        )
    except OverflowError:
        # Clear invalid editor state to avoid repeated crashes on rerun.
        st.session_state.pop(editor_key, None)
        st.error("One numeric value is too large for this column type. Please enter a smaller value and try again.")
        edited_df = df_to_show.copy()
else:
    st.dataframe(
        df_to_show,
        hide_index=True,
        use_container_width=True,
        height=400
    )


# --------------------------------------------------
# Edit Button
# --------------------------------------------------
if st.session_state.edit_mode:
    st.warning("⚠️ Before saving, press Enter or click outside the cell to confirm edits.")
    if st.button("Save Changes", use_container_width=True):
        changes_df = get_changed_rows(edited_df, st.session_state.original_df)
        if changes_df.empty:
            st.info("No changes detected.")
        else:
            try:
                validation_errors = validate_changes_against_schema(changes_df)
                if validation_errors:
                    st.error("Validation failed. Please fix the following values:")
                    for msg in validation_errors:
                        st.caption(f"- {msg}")
                    st.stop()

                change_log_df = build_change_log(changes_df, st.session_state.original_df)
                merge_changes(changes_df)
                log_pending_changes(change_log_df)

                # Refresh base data so the UI shows the updated table
                refresh_data()

                st.session_state.edit_mode = False

                st.success("✅ Changes saved successfully.")
                time.sleep(2)
                st.rerun()
            except Exception:
                logger.exception("Write-back failed")
                st.error("Error while saving changes. Please try again or contact support.")

else:
    if st.button("Edit Table", use_container_width=True):
        st.session_state.original_df = st.session_state.df.copy(deep=True)
        st.session_state.edit_mode = True
        st.rerun()
