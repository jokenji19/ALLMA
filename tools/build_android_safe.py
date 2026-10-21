import argparse
import configparser
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
        ROOT / "libs_custom",
        ROOT / "benchmarks",
    ]
    include_files = [
        ROOT / "main.py",
        ROOT / "buildozer.spec",
        ROOT / "pack_brain.py",
        ROOT / "tools" / "verify_android_apk.py",
        ROOT / "service.py",
        ROOT / "AndroidManifest.xml",
        ROOT / "benchmark_iq.py",
        ROOT / "reproduce_memory_fail.py",
        ROOT / "verify_soul.py",
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


def android_toolchain_ready():
    """Buildozer's clean command requires the p4a checkout as its cwd."""
    config = configparser.ConfigParser(interpolation=None)
    config.read(ROOT / 'buildozer.spec', encoding='utf-8')
    source = config.get('app', 'p4a.source_dir', fallback='').strip()
    if source:
        checkout = Path(source).expanduser()
    else:
        build_dir = Path(config.get('buildozer', 'build_dir', fallback='.buildozer')).expanduser()
        checkout = build_dir / 'android/platform/python-for-android'
    if not checkout.is_absolute():
        checkout = ROOT / checkout
    return checkout.is_dir()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    state_path = ROOT / ".buildozer" / "allma_build_state.json"
    if not args.dry_run:
        run_command([sys.executable, "pack_brain.py"])
    current_hash = compute_hash()
    previous_state = load_state(state_path)
    inputs_changed = previous_state is None or previous_state.get("hash") != current_hash
    needs_clean = inputs_changed and android_toolchain_ready()

    if args.dry_run:
        print("clean_required" if needs_clean else "clean_not_required")
        return

    if needs_clean:
        run_command(["buildozer", "android", "clean"])
    run_command(["buildozer", "android", "debug"])
    apks = list((ROOT / "bin").glob("*.apk"))
    if not apks:
        raise RuntimeError("Build completed without an APK")
    apk = max(apks, key=lambda path: path.stat().st_mtime_ns)
    run_command([sys.executable, "tools/verify_android_apk.py", str(apk)])
    save_state(state_path, {"hash": current_hash})


if __name__ == "__main__":
    main()
