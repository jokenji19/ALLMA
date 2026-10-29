"""Extract the exact optional Hexagon backend from the verified upstream release."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import tarfile

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE_SHA='831a28efeb992108b84d54c5b7538388eba2978d567175e5cfd9843222c6c03d'
SOURCE_COMMIT='0c1e57098bba43ac29e6e3b677cdceebdd22334f'
ORIGINALS={
    'libggml-hexagon.so':'c41518fc003b2f46ceaccb0be968b990a572fea5f5860735507e0b18dd1d26f0',
    'libggml-htp-v79.so':'63684ca64d6a9913fd2e4f0e1001dd212e87a17c8c23145553bddabbf89c907a',
}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('archive',type=Path);args=parser.parse_args()
    with args.archive.open('rb') as f:
        if hashlib.file_digest(f,'sha256').hexdigest()!=ARCHIVE_SHA:raise ValueError('Upstream archive mismatch')
    destination=ROOT/'libs/native_backend/hexagon';destination.mkdir(exist_ok=True)
    files={}
    with tarfile.open(args.archive) as archive:
        for name,digest in ORIGINALS.items():
            member=archive.getmember('llama-b11312/lib/'+name)
            if not member.isfile() or member.size>10_000_000:raise ValueError('Unexpected binary entry')
            payload=archive.extractfile(member).read()
            if hashlib.sha256(payload).hexdigest()!=digest:raise ValueError('Unexpected upstream binary')
            filename=name if name=='libggml-hexagon.so' else name+'.bin'
            path=destination/filename;path.write_bytes(payload)
            if name=='libggml-hexagon.so':
                strip=ROOT/'.buildozer_local/android/platform/android-ndk-r27d/toolchains/llvm/prebuilt/darwin-x86_64/bin/llvm-strip'
                subprocess.run([str(strip),'--strip-unneeded',str(path)],check=True)
            files[filename]=hashlib.sha256(path.read_bytes()).hexdigest()
        (destination/'LICENSE.txt').write_bytes(archive.extractfile('llama-b11312/LICENSE').read())
    metadata={'release':'b11312','source_commit':SOURCE_COMMIT,'archive_sha256':ARCHIVE_SHA,
              'source_url':'https://github.com/ggml-org/llama.cpp/releases/tag/b11312',
              'architecture':'v79','role':'decider','files':files,'upstream_binary_sha256':ORIGINALS}
    (destination/'manifest.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print(json.dumps(metadata,indent=2))

if __name__=='__main__':main()
