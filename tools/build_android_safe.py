import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def iter_files():
    include_dirs = [
        ROOT / "allma_model",
        ROOT / "assets",
        ROOT / "libs" / "recipes",
    ]
    include_files = [
        ROOT / "main.py",
        ROOT / "buildozer.spec",
        ROOT / "pack_brain.py",
    ]
    exclude_dirs = {".git", ".buildozer", "__pycache__", "unpacked_brain", "bin", "venv", ".venv"}
    exclude_exts = {".pyc", ".bak"}

    for path in include_files:
        if path.exists():
            yield path

    for base in include_dirs:
        if not base.exists():
            continue
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for name in files:
                if name == ".DS_Store":
                    continue
                if any(name.endswith(ext) for ext in exclude_exts):
                    continue
                yield Path(root) / name


def compute_hash():
    hasher = hashlib.sha256()
    for path in sorted(iter_files()):
        relative = path.relative_to(ROOT).as_posix()
        hasher.update(relative.encode("utf-8"))
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                hasher.update(chunk)
    return hasher.hexdigest()


def load_state(state_path: Path):
    if not state_path.exists():
        return None
    try:
        with open(state_path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return None


def save_state(state_path: Path, state: dict):
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with open(state_path, "w", encoding="utf-8") as handle:
        json.dump(state, handle)


def run_command(command: list):
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode != 0:
        sys.exit(result.returncode)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    state_path = ROOT / ".buildozer" / "allma_build_state.json"
    current_hash = compute_hash()
    previous_state = load_state(state_path)
    needs_clean = previous_state is None or previous_state.get("hash") != current_hash

    if args.dry_run:
        print("clean_required" if needs_clean else "clean_not_required")
        return

    run_command([sys.executable, "pack_brain.py"])
    if needs_clean:
        run_command(["buildozer", "android", "clean"])
    run_command(["buildozer", "android", "debug"])
    save_state(state_path, {"hash": current_hash})


if __name__ == "__main__":
    main()
