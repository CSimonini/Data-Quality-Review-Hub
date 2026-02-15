The file `constants.py` is used to centralize all application-wide constant values.

Storing constants in a dedicated module provides several benefits:

- Improves readability of the code.
- Avoids hard-coded values scattered across the application.
- Makes configuration changes easier and safer.
- Supports future scalability of the project.

This design follows common software engineering best practices.

- `MAX_ROWS = 50` - defines the maximum number of records that will be displayed in the editable table within the Streamlit application. The value `50` represents a balanced trade-off between visibility and performance for an interactive editing experience.