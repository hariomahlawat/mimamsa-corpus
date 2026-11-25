"""Independent fixture for the integration branch's offline backup verify CLI."""
import argparse
import hashlib
import json
import platform
import subprocess
import sys
import tempfile
from pathlib import Path

PAYLOADS = {'native/source.pdf': b'synthetic copy A\n', 'meta/source.json': b'{"copy":"SYNTH-A"}\n'}
CASES = {
    'BKP-01': ('unchanged', 0, 0, 0),
    'BKP-02': ('same-size byte change', 1, 1, 0),
    'BKP-03': ('missing file', 1, 1, 0),
    'BKP-04': ('unlisted file', 1, 0, 1),
    'BKP-05': ('creation-time mismatch', 1, 1, 0),
}


def synthesize(directory, test_id):
    items = []
    for name, payload in PAYLOADS.items():
        path = directory / 'data' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        exact_hash = hashlib.sha256(payload).hexdigest()
        git_hash = hashlib.sha1(f'blob {len(payload)}\0'.encode() + payload).hexdigest()
        items.append({
            'path': name, 'size': len(payload), 'computed_sha256': exact_hash,
            'lfs_sha256': exact_hash if name.endswith('.pdf') else None,
            'git_oid': git_hash if name.endswith('.json') else None,
            'status': 'BYTE_VERIFIED',
        })
    mismatch = []
    if test_id == 'BKP-02':
        (directory / 'data/native/source.pdf').write_bytes(b'X' + PAYLOADS['native/source.pdf'][1:])
    elif test_id == 'BKP-03':
        (directory / 'data/native/source.pdf').unlink()
    elif test_id == 'BKP-04':
        (directory / 'data/unlisted.txt').write_bytes(b'synthetic unlisted control')
    elif test_id == 'BKP-05':
        mismatch.append('native/source.pdf')
    (directory / 'BACKUP_MANIFEST.json').write_text(json.dumps({
        'repo': 'synthetic/acceptance', 'revision': 'a' * 40, 'files': len(items),
        'bytes': sum(len(payload) for payload in PAYLOADS.values()),
        'only_prefix': None, 'items': items, 'mismatches': mismatch, 'excluded_restricted': [],
    }), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backup-script', type=Path, required=True)
    script = parser.parse_args().backup_script.resolve()
    print(f'{platform.platform()} / Python {platform.python_version()}', flush=True)
    failed = False
    for test_id, (label, code, errors, extras) in CASES.items():
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            synthesize(directory, test_id)
            result = subprocess.run([sys.executable, '-B', str(script), 'verify', '--dest', str(directory)],
                                    capture_output=True, text=True, timeout=10, check=False)
            try:
                summary = json.loads(result.stdout.splitlines()[0])
                actual = (result.returncode, summary['failed'], summary['unexpected_files'])
            except (ValueError, IndexError, KeyError):
                actual = ('malformed result', result.returncode)
            success = actual == (code, errors, extras)
            failed |= not success
            print(f'{test_id} {"Passed" if success else "Failed"} — {label} — {actual}')
    return int(failed)


if __name__ == '__main__':
    raise SystemExit(main())
