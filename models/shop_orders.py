import pandas as pd
import streamlit as st

from snowflake.snowpark import Session
from constants import PRIMARY_KEY, LOCK_COL, DATABASE, SCHEMA, TABLE, ORDER_BY, PENDING_TABLE, PENDING_STAGE_TABLE

BASE_MERGE_STAGE_TABLE = "STREAMLIT_TABLE_BASE_CHANGES"
# from snowflake.snowpark.context import get_active_session

# -----------------------------
# Streamlit Page Setup
# -----------------------------
st.set_page_config(page_title="Snowflake Data Review & Edit Console", layout="wide")
st.title("Snowflake Data Review & Edit Console")

#----------------------------------------------
## ----- CONNECTION -----  ##
## ----- CREATE SESSION -----  ##

# -----------------------------
# Snowflake UI Connection
# -----------------------------

# Get the current Snowflake session
# session = get_active_session()


# -----------------------------
# Snowflake VSCode Connection
# -----------------------------

# Build Snowpark connection parameters from secrets
connection_parameters = {
    "account": st.secrets["connections"]["feb_2026_trial"]["account"]
    ,"user": st.secrets["connections"]["feb_2026_trial"]["user"]
    ,"password": st.secrets["connections"]["feb_2026_trial"]["password"]
    # ,"role": st.secrets["connections"]["dec_2025_trial"]["role"]
    # ,"warehouse": st.secrets["connections"]["dec_2025_trial"]["warehouse"]
    # ,"database": st.secrets["connections"]["dec_2025_trial"]["database"]
    # ,"schema": st.secrets["connections"]["dec_2025_trial"]["schema"]
}

# Create Snowpark session
session = Session.builder.configs(connection_parameters).create()

#----------------------------------------------
#----------------------------------------------

# -----------------------------
# Functions
# -----------------------------

# ---- Change Columns Names  ---- #

def clean_column_names(df):
    def format_col(col):
        return ' '.join(
            'ID' if word.lower() == 'id' else word.capitalize()
                for word in col.split('_')
        )

    df.columns = [format_col(col) for col in df.columns]

    
    # Change column names manually
    # df.rename(columns={"Custid": "Customer ID"}, inplace=True)

    return df


# -------------- Automatic Conversion of Datatypes -------------- #
# Apply tags to the columns for downstream filters/UI
column_tags = {}

# Detect numerics and skip datetime parsing
def is_numeric(series):
    # If the series is entirely numeric (ints or floats), skip it
    return pd.api.types.is_numeric_dtype(series)

def auto_convert_dtypes(df):

    # Normalize base dtypes first (nullable numerics/strings)
    df = df.convert_dtypes()

    # Reuse a single midnight time to detect date-only columns
    midnight = pd.Timestamp(0).time()

    for col in df.columns:
        if is_numeric(df[col]):
            continue

        # Parse once; only accept the column if all values match a known format
        parsed = pd.to_datetime(df[col], format="%Y-%m-%d %H:%M:%S%z", errors="coerce")
        if not parsed.notna().all():
            parsed = pd.to_datetime(df[col], format="%Y-%m-%d", errors="coerce")

        if parsed.notna().all():
            df[col] = parsed
            column_tags[col] = {"type": "timestamp"}

            # Store date bounds for filter defaults
            min_date = parsed.min().date()
            max_date = parsed.max().date()
            column_tags[col]["min_date"] = min_date
            column_tags[col]["max_date"] = max_date

            if (parsed.dt.time == midnight).all():
                df[col] = parsed.dt.date
                column_tags[col]["type"] = "date"

                column_tags[col]["min_date"] = min_date
                column_tags[col]["max_date"] = max_date

    return df

# -----------------------------
# Load Data Into the App
# -----------------------------
@st.cache_data(ttl=60)

def load_data() -> pd.DataFrame:
    order_clause = f" ORDER BY {ORDER_BY}" if ORDER_BY else ""
    df = session.sql(f"""
        SELECT *
        FROM {DATABASE}.{SCHEMA}.{TABLE}{order_clause}
    """).to_pandas()

    df = clean_column_names(df)

    df = auto_convert_dtypes(df)

    return df



def _db_col_name(display_col: str) -> str:
    return display_col.upper().replace(" ", "_")


def get_table_schema_metadata() -> pd.DataFrame:
    sql_clause = f"""
        select
            column_name,
            data_type,
            character_maximum_length,
            numeric_precision,
            numeric_scale
        from {DATABASE}.information_schema.columns
        where table_schema = '{SCHEMA}'
          and table_name = '{TABLE}'
    """
    return session.sql(sql_clause).to_pandas()


def validate_changes_against_schema(changes_df: pd.DataFrame) -> list[str]:
    """Validate edited values against Snowflake column limits before merge."""
    from decimal import Decimal, InvalidOperation

    if changes_df.empty:
        return []

    metadata = get_table_schema_metadata()
    if metadata.empty:
        return []

    meta = metadata.set_index("COLUMN_NAME")
    errors: list[str] = []

    for display_col in changes_df.columns:
        db_col = _db_col_name(display_col)
        if db_col not in meta.index:
            continue

        row = meta.loc[db_col]
        dtype = str(row["DATA_TYPE"]).upper()

        # Enforce VARCHAR length constraints (e.g., ORDER_STATUS VARCHAR(1)).
        if "CHAR" in dtype or "TEXT" in dtype or "STRING" in dtype:
            max_len = row.get("CHARACTER_MAXIMUM_LENGTH")
            if pd.notna(max_len):
                max_len_int = int(max_len)
                series = changes_df[display_col].dropna().astype(str)
                too_long = series[series.str.len() > max_len_int]
                if not too_long.empty:
                    sample = too_long.iloc[0]
                    errors.append(
                        f"{display_col}: max length is {max_len_int}, received '{sample}'"
                    )
            continue

        # Enforce NUMBER(p,s) precision/scale constraints.
        if dtype in {"NUMBER", "DECIMAL", "NUMERIC", "FIXED"}:
            precision = row.get("NUMERIC_PRECISION")
            scale = row.get("NUMERIC_SCALE")
            if pd.notna(precision):
                precision_int = int(precision)
                scale_int = int(scale) if pd.notna(scale) else 0

                for value in changes_df[display_col].dropna():
                    try:
                        dec_value = Decimal(str(value)).copy_abs()
                    except (InvalidOperation, ValueError):
                        errors.append(
                            f"{display_col}: value '{value}' is not a valid NUMBER({precision_int},{scale_int})"
                        )
                        break

                    digits = dec_value.as_tuple().digits
                    exponent = dec_value.as_tuple().exponent

                    if exponent >= 0:
                        int_digits = len(digits) + exponent
                        frac_digits = 0
                    else:
                        int_digits = max(len(digits) + exponent, 0)
                        frac_digits = -exponent

                    total_digits = int_digits + frac_digits
                    max_int_digits = max(precision_int - scale_int, 0)

                    if frac_digits > scale_int:
                        errors.append(
                            f"{display_col}: value '{value}' has scale {frac_digits} but max is {scale_int}"
                        )
                        break

                    if int_digits > max_int_digits or total_digits > precision_int:
                        errors.append(
                            f"{display_col}: value '{value}' exceeds NUMBER({precision_int},{scale_int})"
                        )
                        break

    return errors

# -----------------------------
# Merge Changes into Snowflake Table
# -----------------------------

# takes a pandas df as input
# This function receives only the rows that changed in the UI
def merge_changes(changes_df: pd.DataFrame) -> int:

    # Snowpark write_pandas ignores non-standard indexes; normalize to avoid warnings.
    changes_df = changes_df.reset_index(drop=True)
    changes_df.columns = [col.upper().replace(" ", "_") for col in changes_df.columns]

    # if there's no delta, skip
    if changes_df.empty:
        return 0

    session.write_pandas(
        changes_df,
        table_name=BASE_MERGE_STAGE_TABLE,
        database=DATABASE,
        schema=SCHEMA,
        overwrite=True,
        auto_create_table=True,
        table_type="temp",
        use_logical_type=True,
        quote_identifiers=False
    )

    pk_cols = PRIMARY_KEY if isinstance(PRIMARY_KEY, (list, tuple)) else [PRIMARY_KEY]
    pk_cols_db = [col.upper().replace(" ", "_") for col in pk_cols]
    lock_col = LOCK_COL.upper().replace(" ", "_") if LOCK_COL else None

    exclude_cols = set(pk_cols_db)
    if lock_col:
        exclude_cols.add(lock_col)

    update_cols = [
        c for c in changes_df.columns
        if c not in exclude_cols
    ]

    # create dynamically the text clause to add to the SQL clause next
    set_clause = ", ".join(
        [f'prd.{c} = src.{c}' for c in update_cols]
    )

    on_clause = " and ".join([f"prd.{c} = src.{c}" for c in pk_cols_db])

    if lock_col:
        sql_clause = f"""
        merge into {DATABASE}.{SCHEMA}.{TABLE}                  prd
        using {DATABASE}.{SCHEMA}.{BASE_MERGE_STAGE_TABLE}               src
        on {on_clause}
        when matched then update set
          {set_clause},
          prd.{lock_col} = current_timestamp()
    """
    else:
        sql_clause = f"""
        merge into {DATABASE}.{SCHEMA}.{TABLE}                  prd
        using {DATABASE}.{SCHEMA}.{BASE_MERGE_STAGE_TABLE}               src
        on {on_clause}
        when matched then update set
          {set_clause}
    """

    session.sql(sql_clause).collect()
    return len(changes_df)




def ensure_pending_table_exists(pk_cols_db: list[str]) -> None:
    # Persistent queue table for approval workflow; created automatically on first save.
    pk_defs = ",\n            ".join([f"{col} VARCHAR" for col in pk_cols_db])
    sql_clause = f"""
        create table if not exists {DATABASE}.{SCHEMA}.{PENDING_TABLE} (
            {pk_defs},
            column_name STRING,
            old_value VARIANT,
            new_value VARIANT,
            changed_by STRING,
            changed_at TIMESTAMP_NTZ default current_timestamp(),
            approval_status STRING default 'PENDING'
        )
    """
    session.sql(sql_clause).collect()

def log_pending_changes(change_log_df: pd.DataFrame) -> int:
    # Normalize index so write_pandas does not warn about ignored index values.
    change_log_df = change_log_df.reset_index(drop=True)
    if change_log_df.empty:
        return 0

    session.write_pandas(
        change_log_df,
        table_name=PENDING_STAGE_TABLE,
        database=DATABASE,
        schema=SCHEMA,
        overwrite=True,
        auto_create_table=True,
        table_type="temp",
        use_logical_type=True,
        quote_identifiers=False
    )

    pk_cols = PRIMARY_KEY if isinstance(PRIMARY_KEY, (list, tuple)) else [PRIMARY_KEY]
    pk_cols_db = [col.upper().replace(" ", "_") for col in pk_cols]

    ensure_pending_table_exists(pk_cols_db)

    insert_cols = ",\n            ".join(pk_cols_db + ["column_name", "old_value", "new_value", "changed_by"])
    select_cols = ",\n            ".join(
        pk_cols_db + ["column_name", "to_variant(old_value)", "to_variant(new_value)", "current_user()"]
    )

    sql_clause = f"""
        insert into {DATABASE}.{SCHEMA}.{PENDING_TABLE} (
            {insert_cols}
        )
        select
            {select_cols}
        from {DATABASE}.{SCHEMA}.{PENDING_STAGE_TABLE}
    """

    session.sql(sql_clause).collect()
    return len(change_log_df)

