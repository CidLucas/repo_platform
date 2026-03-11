vizu_google_suite_client

Client library to interact with Google Sheets, Gmail and Calendar.

Purpose
- Provide small async/await wrappers for Google Workspace APIs.
- Accept already-validated OAuth tokens (access/refresh) and perform refresh when needed.

Structure
- base.py: Base client with refresh logic
- sheets/: Sheets client + models
- gmail/: Gmail client + models
- calendar/: Calendar client + models

See the project-level `Google_integration.md` for architecture and integration notes.