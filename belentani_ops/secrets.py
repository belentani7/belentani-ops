import os
import re
from pathlib import Path

from . import util
from .config import SECRET_PATTERNS

SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", ".mypy_cache",
    ".pytest_cache", "dist", "build", ".next", ".cache", "site-packages",
    "AppData", ".npm", ".cargo", ".ollama", ".lmstudio",
}

SKIP_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip",
    ".gz", ".tar", ".7z", ".rar", ".mp3", ".mp4", ".wav", ".onnx",
    ".bin", ".exe", ".dll", ".so", ".dylib", ".woff", ".woff2", ".ttf",
    ".pyc", ".lock", ".db", ".sqlite", ".sqlite3",
}

COMPILED = [(name, re.compile(pattern)) for name, pattern in SECRET_PATTERNS]
COMPILED.append(("env_assign", re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]([^'\"]{12,})['\"]")))


def _should_scan(path):
    if path.suffix.lower() in SKIP_EXT:
        return False
    if path.name in {"package-lock.json", "yarn.lock", "pnpm-lock.yaml"}:
        return False
    return True


def scan_paths(roots, max_bytes=2_000_000, max_files=20000):
    hits = []
    scanned = 0
    for root in roots:
        base = Path(root)
        if not base.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(base, onerror=lambda e: None):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for name in filenames:
                if scanned >= max_files:
                    return hits, scanned, True
                path = Path(dirpath) / name
                if not _should_scan(path):
                    continue
                try:
                    if path.stat().st_size > max_bytes:
                        continue
                except OSError:
                    continue
                scanned += 1
                hits.extend(scan_file(path))
    return hits, scanned, False


def scan_file(path):
    hits = []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return hits
    for lineno, line in enumerate(text.splitlines(), 1):
        if len(line) > 4000:
            continue
        for name, pattern in COMPILED:
            m = pattern.search(line)
            if m:
                raw = m.group(0)
                if name == "env_assign" and m.lastindex and m.lastindex >= 2:
                    raw = m.group(2)
                hits.append({
                    "file": str(path), "line": lineno, "kind": name,
                    "masked": util.mask(raw),
                })
                break
    return hits


def audit_env_files(roots):
    found = []
    for root in roots:
        base = Path(root)
        if not base.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(base, onerror=lambda e: None):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for name in filenames:
                if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
                    found.append(str(Path(dirpath) / name))
    return found


def gitignore_covers_env(roots):
    missing = []
    for root in roots:
        base = Path(root)
        if not base.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(base, onerror=lambda e: None):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            if ".git" in dirnames:
                gi = Path(dirpath) / ".gitignore"
                if gi.is_file():
                    try:
                        content = gi.read_text(encoding="utf-8", errors="ignore")
                    except OSError:
                        continue
                    if ".env" not in content:
                        missing.append(str(Path(dirpath)))
                else:
                    missing.append(str(Path(dirpath)))
    return missing


def rotation_checklist():
    return [
        "Alibaba DASHSCOPE_API_KEY (Token Plan) - panel DashScope",
        "Alibaba BAILIAN_API_KEY (Standard) - panel Bailian",
        "HuggingFace HF_API_KEY - settings/tokens",
        "OpenRouter OPENROUTER_API_KEY - keys",
        "Groq GROQ_API_KEY - console keys",
        "GitHub GITHUB_TOKEN (fine-grained) - developer settings",
        "Gmail GMAIL_APP_PASSWORD - app passwords",
        "Cualquier sk-* / hf_* / gsk_* detectada en el scan",
    ]


def scan_report(cfg):
    hits, scanned, truncated = scan_paths(cfg.scan_roots)
    return {
        "hits": hits,
        "scanned": scanned,
        "truncated": truncated,
        "env_files": audit_env_files(cfg.scan_roots),
        "gitignore_missing": gitignore_covers_env(cfg.scan_roots),
        "rotation": rotation_checklist(),
    }
