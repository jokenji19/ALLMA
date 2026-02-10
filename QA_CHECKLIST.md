# ALLMA QA & DEPLOYMENT PROTOCOL
> **CRITICAL:** Do NOT deploy or push a build without completing this checklist.

## 1. Integrity Checks
- [ ] **Main Entry Point**: Verify `main.py` is NOT truncated and contains the full execution footer (lines > 150).
- [ ] **Blob Content**: Verify `allma_model` inside `ZIP_DATA` contains all required sub-packages (`ui`, `core`, `utils`).
- [ ] **Critical Files**: Ensure `app_entry.py`, `chat_view.py`, and `setup_view.py` exist in the source map.
- **[ ] CHECK 7: Code Integrity**
    - [ ] Did you verify the file content after editing?
    - [ ] Are all class methods properly defined (check for missing `def`)?
    - [ ] Are indentations correct?

## 5. Final Decisional Verification
- [ ] **Extraction Simulation**: Run `main.py` locally. Does it extract to `unpacked_brain`?
- [ ] **Dependecy Check**: Are all imports (Kivy, requests, internal libs) resolvable?
- [ ] **Flow Test**:
    1. **Installer**: Does the loading bar appear?
    2. **Setup**: Does it prompt for model download (or skip if present)?
    3. **Chat**: Does the TextInput appear and accept input?

## 3. Deployment Safety
- [ ] **Clean Build**: Did you remove temporary files (`tools/inject_blob.py`, `debug_*.py`)?
- [ ] **Pack Brain**: Did you run `python3 pack_brain.py` to update `ZIP_DATA`?
- [ ] **Build Safe**: Did you run `python3 tools/build_android_safe.py` for a clean build when needed?
- [ ] **Fresh Build**: Did you run `buildozer android clean` before `buildozer android debug`?
- [ ] **Version Bump**: Is the version number in `buildozer.spec` updated?
- [ ] **Git Status**: Are there uncommitted changes?

---
*Created on 2026-01-16 to preventing missing components in release builds.*
