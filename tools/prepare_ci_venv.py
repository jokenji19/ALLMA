"""Copy the image virtualenv to a writable location for non-root CI builds."""
import os
from pathlib import Path
import shutil
import stat
import sys


def prepare(source: Path, target: Path) -> None:
    source = source.absolute()
    target = target.absolute()
    if target.exists():
        raise FileExistsError(target)
    shutil.copytree(source, target, symlinks=True)
    for root, dirs, files in os.walk(target):
        for name in [*dirs, *files]:
            item = Path(root, name)
            if not item.is_symlink():
                item.chmod(item.stat().st_mode | stat.S_IWUSR)
    old_prefix = (str(source) + '/bin/').encode()
    new_prefix = (str(target) + '/bin/').encode()
    for item in (target / 'bin').iterdir():
        if item.is_symlink() or not item.is_file():
            continue
        with item.open('rb') as f:
            line = f.readline()
            if not line.startswith(b'#!' + old_prefix):
                continue
            rest = f.read()
        item.write_bytes(line.replace(old_prefix, new_prefix, 1) + rest)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('usage: prepare_ci_venv.py SOURCE TARGET')
    prepare(Path(sys.argv[1]), Path(sys.argv[2]))
