"""AUTH-LEDGER shared helpers (stdlib only; offline; deterministic)."""
import csv, hashlib, io, json, os, stat
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
# The package path as reached, WITHOUT resolving symlinks (C8, Fable C-02): a symlinked package must be detectable, so the
# repository pin and the symlink check use this logical path rather than the resolved one.
LOGICAL_PKG = Path(__import__("os").path.abspath(__file__)).parents[1]
AW = PKG.parent
REPO = AW.parents[1]
HEX64 = __import__("re").compile(r"[0-9a-f]{64}")


class LedgerError(Exception):
    """Any integrity, schema, evidence or approval failure. The reader fails closed on it."""


def read_regular_bytes(path):
    """Read a file only if it is a regular file reached without following a symbolic link (C11 reviews CA-01, C11-01/02).

    O_NOFOLLOW refuses a symlink at the final path component, O_NONBLOCK keeps a FIFO from blocking the open, and fstat on
    the open descriptor refuses anything that is not a regular file (FIFO, socket, device, directory). An OSError raised
    by the open, fstat or read becomes a LedgerError. On a platform without O_NOFOLLOW the read fails closed (C11-05).
    Every ledger, decision, review, frozen-pin and pinned-input read goes through here (via sha256_file, read_csv,
    load_json, read_regular_text)."""
    p = str(path)
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_NONBLOCK"):
        raise LedgerError("this platform lacks O_NOFOLLOW/O_NONBLOCK; refusing to read ledger inputs without them")
    try:
        fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError as e:
        raise LedgerError(f"{p}: cannot open as a regular file ({e.__class__.__name__}: {e.strerror})")
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise LedgerError(f"{p}: not a regular file (mode {stat.filemode(st.st_mode)})")
        chunks = []
        while True:
            b = os.read(fd, 1 << 20)
            if not b:
                break
            chunks.append(b)
        return b"".join(chunks)
    except OSError as e:
        raise LedgerError(f"{p}: read failed ({e.__class__.__name__}: {e.strerror})")
    finally:
        os.close(fd)


def read_regular_text(path):
    try:
        return read_regular_bytes(path).decode("utf-8")
    except UnicodeDecodeError as e:
        raise LedgerError(f"{path}: not UTF-8 text ({e})")


def read_csv(path):
    return list(csv.DictReader(io.StringIO(read_regular_text(path), newline="")))


def csv_text(cols, rows):
    b = io.StringIO()
    w = csv.DictWriter(b, fieldnames=cols, lineterminator="\n", extrasaction="raise")
    w.writeheader()
    for r in rows:
        w.writerow({c: r.get(c, "") for c in cols})
    return b.getvalue()


def sha256_file(path):
    return hashlib.sha256(read_regular_bytes(path)).hexdigest()


def sha256_text(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def load_json(path):
    return json.loads(read_regular_text(path))
