"""Bundle pinned upstream voice sources for the Android release, never models/state.

Downloads source archives only. It does not build or execute upstream code.
The original upstream recipes and license files remain inside the archives.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import re
import tarfile
import time
import urllib.request

SHERPA_VERSION = '1.12.20'
SHERPA_URL = f'https://codeload.github.com/k2-fsa/sherpa-onnx/tar.gz/refs/tags/v{SHERPA_VERSION}'
SHERPA_SHA256 = '1fdd05cd2552875a2d9dae13e415447ef422d939778b89be0bc4ed83ea2b9aef'


def digest(path):
    with path.open('rb') as reader:
        return hashlib.file_digest(reader, 'sha256').hexdigest()


def fetch(entry, directory):
    target = directory / entry['filename']
    expected = entry.get('sha256')
    if not target.exists() or (expected and digest(target) != expected):
        temporary = target.with_suffix(target.suffix + '.part')
        for attempt in range(3):
            try:
                request = urllib.request.Request(entry['url'], headers={'User-Agent': 'ALLMA-source-release/0.9.1'})
                with urllib.request.urlopen(request, timeout=60) as response, temporary.open('wb') as writer:
                    while chunk := response.read(1024 * 1024):
                        writer.write(chunk)
                actual = digest(temporary)
                if expected and actual != expected:
                    raise ValueError('Source checksum mismatch: ' + entry['filename'])
                temporary.replace(target)
                break
            except Exception:
                temporary.unlink(missing_ok=True)
                if attempt == 2:
                    raise
                time.sleep(attempt + 1)
    return dict(entry, sha256=digest(target), bytes=target.stat().st_size)


def prepare(directory):
    directory.mkdir(parents=True, exist_ok=True)
    sherpa = fetch({'filename':f'sherpa-onnx-v{SHERPA_VERSION}.tar.gz',
                    'url':SHERPA_URL, 'sha256':SHERPA_SHA256}, directory)
    entries = []
    with tarfile.open(directory / sherpa['filename']) as package:
        for member in package.getmembers():
            if not member.isfile() or '/cmake/' not in member.name or not member.name.endswith('.cmake'):
                continue
            content = package.extractfile(member).read().decode('utf-8')
            for variable, url in re.findall(r'set\(\s*(\w+_URL)\s+"(https://[^"\s]+)"', content):
                if not any(marker in url for marker in ('/archive/', '/tar.gz/', '/zip/')):
                    continue
                # Pinned source archives; GPU/CPU binary downloads are excluded.
                hashes = re.findall(r'set\(\s*' + re.escape(variable[:-4]) + r'_HASH\s+"SHA256=([a-f0-9]{64})"', content)
                filename = url.rsplit('/', 1)[-1]
                if '/archive/' in url and 'github.com/' in url:
                    owner_repo, ref = url.split('github.com/', 1)[1].split('/archive/', 1)
                    extension = '.tar.gz' if ref.endswith('.tar.gz') else '.zip'
                    ref = ref.removesuffix(extension)
                    url = f'https://codeload.github.com/{owner_repo}/' + ('tar.gz/' if extension == '.tar.gz' else 'zip/') + ref
                entry = {'filename':variable[:-4] + '-' + filename, 'url':url,
                         'recipe':member.name.split('/', 1)[1]}
                if hashes:
                    entry['sha256'] = hashes[0]
                entries.append(entry)
    entries.append({'filename':'onnxruntime-v1.17.1.tar.gz',
                    'url':'https://codeload.github.com/microsoft/onnxruntime/tar.gz/refs/tags/v1.17.1',
                    'recipe':'build-android-arm64-v8a.sh'})
    results = [sherpa]
    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs = {pool.submit(fetch, entry, directory):entry for entry in entries}
        for job in as_completed(jobs):
            result = job.result()
            results.append(result)
            print(result['filename'], result['bytes'], flush=True)
    results.sort(key=lambda entry:entry['filename'])
    (directory/'SOURCE_MANIFEST.json').write_text(json.dumps({
        'sherpa_onnx':SHERPA_VERSION, 'sources':results,
        'scope':'Pinned upstream source snapshots and original build recipes. No user data or model weights.'
    }, indent=2) + '\n')
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    prepare(args.directory)
