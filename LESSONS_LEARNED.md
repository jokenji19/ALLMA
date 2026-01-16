# ALLMA Project - Lessons Learned & Error Log

> **Purpose:** This document records critical errors, their root causes, and the specific protocols implemented to prevent them from happening again.
> **Rule:** Before starting a complex task, review this log to ensure past mistakes are not repeated.

## 2026-01-16: Build 153 Crash & Deployment Failures

### 1. The Truncated `main.py`
*   **Error:** The application crashed immediately on startup (open & close).
*   **Root Cause:** The `inject_blob.py` script (or manual editing) replaced the `ZIP_DATA` variable but inadvertently deleted or failed to append the execution logic (Kivy App class and `if __name__` block).
*   **Lesson:** Never assume a file is correct just because it exists.
*   **Prevention:** `QA_CHECKLIST.md` -> Check 1: Verify `main.py` has the footer code (> 150 lines).

### 2. Missing "Internal" Components
*   **Error:** Build 153.1 would have failed because it tried to import `SetupView` and `ChatView` which did not exist in the `allma_model` directory being zipped.
*   **Root Cause:** Focused entirely on fixing the "Container" (`main.py`) without verifying the "Content" (`allma_model` source code).
*   **Lesson:** Fixing the delivery mechanism (zip extraction) is useless if the payload is empty.
*   **Prevention:** `QA_CHECKLIST.md` -> Check 2: Explicitly verify `ui/setup_view.py` and `ui/chat_view.py` exist before zipping.

### 3. Model Filename Sync Failure
*   **Error:** The Downloader was set to download `Gemma-3n`, but the LLM Wrapper was hardcoded to look for `Gemma-2`.
*   **Root Cause:** Changing a dependency (Model Version) in one place (`ModelDownloader`) without updating its consumer (`MobileGemmaWrapper`).
*   **Lesson:** Configuration parameters (filenames, versions, APIs) must be defined in a single shared place or explicitly synced.
*   **Prevention:** `QA_CHECKLIST.md` -> Check 3: Verify filename consistency between Downloader and Wrapper.

---
*End of Log*
