import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_NO_COLOR = os.environ.get("NO_COLOR") or not sys.stdout.isatty()

COLORS = {
    "reset": "\033[0m", "red": "\033[31m", "green": "\033[32m",
    "yellow": "\033[33m", "blue": "\033[34m", "magenta": "\033[35m",
    "cyan": "\033[36m", "bold": "\033[1m", "dim": "\033[2m",
}


def c(text, color):
    if _NO_COLOR or color not in COLORS:
        return str(text)
    return f"{COLORS[color]}{text}{COLORS['reset']}"


def ok(msg):
    print(f"{c('[OK]', 'green')} {msg}")


def warn(msg):
    print(f"{c('[WARN]', 'yellow')} {msg}")


def err(msg):
    print(f"{c('[ERR]', 'red')} {msg}")


def info(msg):
    print(f"{c('[..]', 'cyan')} {msg}")


def head(msg):
    print(c(f"\n=== {msg} ===", "bold"))


def human_bytes(n):
    step = 1024.0
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < step:
            return f"{n:,.1f}{unit}"
        n /= step
    return f"{n:,.1f}PB"


def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def which(name):
    return shutil.which(name)


def run(cmd, cwd=None, timeout=120, env=None, check=False):
    merged = dict(os.environ)
    if env:
        merged.update(env)
    try:
        proc = subprocess.run(
            cmd, cwd=str(cwd) if cwd else None, capture_output=True,
            text=True, timeout=timeout, env=merged,
            encoding="utf-8", errors="replace",
        )
        return proc.returncode, proc.stdout or "", proc.stderr or ""
    except FileNotFoundError:
        return 127, "", f"command not found: {cmd[0] if cmd else ''}"
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s"
    except Exception as exc:
        return 1, "", str(exc)


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path, data):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return p


def append_jsonl(path, record):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return p


def mask(secret, keep=4):
    if not secret:
        return ""
    s = str(secret)
    if len(s) <= keep * 2:
        return "*" * len(s)
    return f"{s[:keep]}{'*' * (len(s) - keep * 2)}{s[-keep:]}"


def load_env_file(path):
    data = {}
    p = Path(path)
    if not p.is_file():
        return data
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        data[key.strip()] = val.strip().strip('"').strip("'")
    return data


def redact_text(text):
    from .config import SECRET_PATTERNS
    out = text
    for _name, pattern in SECRET_PATTERNS:
        out = re.sub(pattern, lambda m: mask(m.group(0)), out)
    return out


def dir_size(path, limit_files=None):
    total = 0
    count = 0
    p = Path(path)
    if not p.exists():
        return 0, 0
    for root, _dirs, files in os.walk(p, onerror=lambda e: None):
        for name in files:
            try:
                total += (Path(root) / name).stat().st_size
                count += 1
                if limit_files and count >= limit_files:
                    return total, count
            except OSError:
                continue
    return total, count


def confirm(prompt, assume_yes=False):
    if assume_yes:
        return True
    try:
        ans = input(f"{prompt} [y/N] ").strip().lower()
    except EOFError:
        return False
    return ans in ("y", "yes", "s", "si", "sí")


def truncate(text, n=4000):
    text = text or ""
    if len(text) <= n:
        return text
    return text[:n] + f"\n... [truncado {len(text) - n} chars]"
