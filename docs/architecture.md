# Application Architecture

This document describes the architectural design of the Streamlit Editable Table Application built on Snowflake. The architecture prioritizes schema agnosticism, data integrity, and a clear separation of responsibilities.

## Architectural Goals

The application is designed to:
- Work with different Snowflake tables without code rewrites.
- Adapt to schema changes automatically.
- Generate UI behavior dynamically based on data types.
- Preserve data integrity throughout the pipeline.
- Support future write-back, validation, and auditing features.
- Remain readable and intuitive for non-technical users.

## High-Level Architecture

Snowflake  
→ Snowpark Session  
→ Pandas DataFrame  
→ Data Normalization Layer  
→ Session State Storage  
→ UI Rendering Layer (Streamlit)

Each layer has a clearly defined responsibility.

## Layer Responsibilities

### 1) Snowflake Access Layer
Responsible for:
- Establishing Snowpark sessions.
- Executing SQL queries.
- Retrieving raw data.

This layer does not perform UI or transformation logic.

### 2) Data Normalization Layer (`models/shop_orders.py`)
Responsible for:
- Column name normalization.
- Automatic dtype inference.
- Safe datetime detection.
- Date vs timestamp distinction.
- Producing a strongly typed DataFrame.
- Merging user edits back into Snowflake via `merge_changes`.

### 3) Session State Layer (`init_state.py`)
Responsible for:
- Persisting the main DataFrame across reruns.
- Storing filter states.
- Managing edit state and data refresh after write-back.

### 4) Constants Layer (`constants.py`)
Responsible for:
- Centralizing configuration values.
- Avoiding hard-coded magic numbers.
- Enabling global behavior control.

### 5) UI Layer (`app.py`)
Responsible for:
- Rendering tables.
- Displaying filters.
- Managing user interaction.
- Never performing raw data transformations.
- Disabling PK/LOCK columns during edit mode to protect data integrity.

### 6) Controllers Layer (`controllers/`)
Responsible for:
- Encapsulating business logic (filters, edits, future write-back).
- Keeping the UI thin and predictable.

## Data Flow

1) Snowflake data is loaded via Snowpark.  
2) Data is converted to Pandas.  
3) Column names are cleaned.  
4) Data types are inferred and normalized.  
5) The DataFrame is stored in `session_state`.  
6) UI components consume `session_state` data.  
7) If edits are saved, changes are merged back into Snowflake and the DataFrame is refreshed.  

```mermaid
flowchart LR
    A[Snowflake: STREAMLIT_TABLE_BASE] -->|Snowpark query| B[Pandas DataFrame]
    B --> C[Type inference + column tags]
    C --> D[Session State]
    D --> E[UI: Filters + Table]
    E -->|Edit + Save| F[Change Log (per column)]
    F --> G[STREAMLIT_PENDING_CHANGES]
    E -->|Merge| A
```

## Data Integrity Principles


- Query targets are configured via constants (DATABASE/SCHEMA/TABLE/ORDER_BY) for schema-agnostic loading.
The architecture enforces:
- No silent type coercion.
- No lossy conversions.
- No implicit schema assumptions.
- No stringification of structured data.

## Schema-Agnostic Strategy

The application never assumes:
- Column names.
- Column order.
- Column data types.

All UI logic is driven by detected types and `column_tags`.

## Type-Aware UI Strategy

Data Type → UI Behavior  
- Numeric → Sliders / numeric filters  
- String → Dropdown / text filters  
- Date → Date picker  
- Datetime → Date range picker  
- Boolean → Checkbox / selectbox  

## Performance Strategy

Performance is managed through:
- Streamlit caching with TTL.
- Session state reuse across reruns.
- Deferred computation via Apply Filters.

## Extensibility

The architecture is designed to support:
- Write-back to Snowflake.
- Change tracking and validation rules.
- Audit logs.
- Pagination.
- Role-based permissions.
- Multi-table navigation.
- Approval workflows that promote changes from base to official tables.

## Separation of Concerns

Layer → Responsibility  
- Models → Data access and normalization  
- State → Persistence across reruns  
- UI → Visualization and interaction  
- Controllers → Business logic  
- Constants → Configuration  

## Error Containment

Errors are isolated per layer:
- Connection errors stay in data access.
- Conversion errors stay in normalization.
- UI errors never corrupt data.

## Design Philosophy

This project follows:
- Engineering-first design.
- Data integrity over convenience.
- Explicit behavior over implicit magic.
- Clarity over cleverness.
- Scalability over shortcuts.

## Architectural Summary

This architecture transforms Streamlit from a scripting tool into a structured application platform, capable of supporting real business workflows safely and predictably.

## Final Principle

> The architecture exists to protect data, users, and future maintainers.

Every design choice in this project serves that purpose.
