# AI Agent Instructions

This project is a production-quality Streamlit application that loads data from Snowflake, displays it in an editable table, and supports dynamic, schema-agnostic filtering and future write-back.

Any AI agent contributing to this repository must strictly follow the architectural, UX, and data integrity principles described below.

---

## 🎯 Project Goals

The application must:

- Be **schema-agnostic**: it should work with different Snowflake tables without code rewrites.
- Automatically infer column data types (numeric, string, date, datetime).
- Convert datetime columns with only midnight timestamps into true date values.
- Generate UI filters dynamically based on column data types.
- Remain usable for **non-technical users**.
- Prioritize clarity, stability, and maintainability over cleverness.

---

## 🧠 Architectural Principles

AI agents must:

- Preserve strong typing of data.
- Never silently corrupt or downgrade data types.
- Avoid converting dates into strings unless explicitly requested for UI display only.
- Respect Streamlit session_state behavior and lifecycle.
- Respect Streamlit caching behavior.
- Avoid hidden side effects in data transformations.
- Keep business logic separated from UI logic.
- Prefer placing reusable business logic in `controllers/` (filters, edits, future write-back).

---

## 🧪 Data Handling Rules

- Datetime detection must be validated before conversion.
- Date-only timestamps must be stored as `datetime.date`, not as strings.
- Invalid datetime columns must remain unchanged.
- Numeric columns must remain numeric.
- No lossy transformations are allowed without explicit justification.
- When time-based filters are required, `column_tags` must include `min_date` and `max_date` bounds.

---

## 🖥 UI Behavior

- Filters must be generated dynamically based on detected column types.
- Default filter values must preserve full dataset visibility (e.g., "All").
- The UI must favor readability for non-technical users.
- Column names must remain human-readable.
- If an **Apply Filters** button is present, stage selections and commit them only on click.

---

## 🛠 Coding Style

AI agents must:

- Prefer readable code over compact tricks.
- Add comments when design decisions affect architecture.
- Avoid unnecessary abstraction.
- Avoid premature optimization.
- Write code as if it will be maintained by another engineer.

---

## 🔍 When Uncertain

If an AI agent is unsure about:

- A design decision,
- A type inference rule,
- A transformation consequence,

It must **ask for clarification instead of guessing**.

---

## 📚 Documentation

When adding or modifying functionality:

- Documentation must be updated accordingly.
- Explanations must include both *what* and *why*.
- Keep docs aligned with current module paths and controller usage.

---

## 🚫 Prohibited Behavior

AI agents must not:

- Introduce silent breaking changes.
- Remove type safety.
- Hardcode schema-specific logic.
- Optimize for demo behavior over production stability.

---

## 🧩 Role of AI Agents

AI agents are considered **engineering collaborators**, not code generators.

They must act as:

- Software engineers,
- System designers,
- Data integrity guardians.

---

## ✅ Final Principle

> This repository favors correctness, clarity, and long-term maintainability over short-term convenience.

Any AI contribution must align with this principle.

