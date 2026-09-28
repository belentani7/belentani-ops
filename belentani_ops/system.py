import os
import shutil
import string
from pathlib import Path

from . import util
from .config import ALLOWED_HOME_DOTDIRS, HOME, JUNK_DOTDIRS


def disk_report(cfg):
    rows = []
    for letter in string.ascii_uppercase:
        root = f"{letter}:\\"
        if not os.path.exists(root):
            continue
        try:
            usage = shutil.disk_usage(root)
        except OSError:
            continue
        free_gb = usage.free / (1024 ** 3)
        if free_gb < cfg.disk_readonly_gb:
            level = "readonly"
        elif free_gb < cfg.disk_block_gb:
            level = "block"
        elif free_gb < cfg.disk_warn_gb:
            level = "warn"
        else:
            level = "ok"
        rows.append({
            "drive": root, "total": usage.total, "free": usage.free,
            "used": usage.used, "free_gb": round(free_gb, 2), "level": level,
        })
    return rows


def disk_guard(cfg, allow_write=True):
    report = disk_report(cfg)
    primary = next((r for r in report if r["drive"].upper().startswith("C")), None)
    if not primary:
        return {"allowed": allow_write, "level": "unknown", "report": report}
    level = primary["level"]
    allowed = allow_write
    if level == "readonly":
        allowed = False
    elif level == "block":
        allowed = allow_write
    if level == "readonly":
        util.err(f"Disco {primary['drive']} < {cfg.disk_readonly_gb}GB: SOLO LECTURA")
    elif level == "block":
        util.warn(f"Disco {primary['drive']} < {cfg.disk_block_gb}GB: bloqueada escritura grande")
    elif level == "warn":
        util.warn(f"Disco {primary['drive']} < {cfg.disk_warn_gb}GB libres ({primary['free_gb']}GB)")
    else:
        util.ok(f"Disco {primary['drive']}: {primary['free_gb']}GB libres")
    return {"allowed": allowed, "level": level, "report": report}


def home_root_guard():
    findings = {"stray_files": [], "junk_dirs": [], "suspicious": []}
    try:
        entries = list(HOME.iterdir())
    except OSError:
        return findings
    for entry in entries:
        name = entry.name
        if entry.is_file():
            findings["stray_files"].append(name)
            continue
        if name.startswith("."):
            if name in JUNK_DOTDIRS:
                findings["junk_dirs"].append(name)
            elif name not in ALLOWED_HOME_DOTDIRS:
                findings["suspicious"].append(name)
        else:
            findings["stray_files"].append(name + "/")
    return findings


def clean_plan(cfg):
    plan = []
    for target in cfg.clean_targets:
        p = Path(target)
        if not p.exists():
            continue
        size, count = util.dir_size(p, limit_files=200000)
        plan.append({"path": str(p), "size": size, "files": count})
    plan.sort(key=lambda x: x["size"], reverse=True)
    return plan


def clean_apply(cfg, plan, assume_yes=False):
    guard = disk_guard(cfg, allow_write=True)
    if guard["level"] == "readonly":
        util.err("Disco en solo lectura; limpieza cancelada")
        return {"deleted": 0, "freed": 0, "errors": ["disco readonly"]}
    freed = 0
    deleted = 0
    errors = []
    for item in plan:
        p = Path(item["path"])
        if not p.exists():
            continue
        if not util.confirm(f"Borrar contenido de {p} ({util.human_bytes(item['size'])})?", assume_yes):
            continue
        for child in p.iterdir():
            try:
                if child.is_dir():
                    shutil.rmtree(child, ignore_errors=False)
                else:
                    child.unlink()
                deleted += 1
            except Exception as exc:
                errors.append(f"{child}: {exc}")
        freed += item["size"]
    return {"deleted": deleted, "freed": freed, "errors": errors}


def top_processes(limit=15):
    code, out, _ = util.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-Process | Sort-Object WorkingSet64 -Descending | "
         f"Select-Object -First {limit} ProcessName,Id,WorkingSet64 | ConvertTo-Json -Compress"],
        timeout=60,
    )
    if code != 0:
        return []
    import json
    try:
        data = json.loads(out)
    except Exception:
        return []
    if isinstance(data, dict):
        data = [data]
    result = []
    for row in data:
        result.append({
            "name": row.get("ProcessName"),
            "pid": row.get("Id"),
            "mem": row.get("WorkingSet64", 0),
        })
    return result


def dotfile_audit():
    present = []
    try:
        for entry in HOME.iterdir():
            if entry.is_dir() and entry.name.startswith("."):
                present.append(entry.name)
    except OSError:
        pass
    return {
        "present": sorted(present),
        "junk": sorted([d for d in present if d in JUNK_DOTDIRS]),
        "unknown": sorted([d for d in present if d not in ALLOWED_HOME_DOTDIRS and d not in JUNK_DOTDIRS]),
    }


def healthcheck(cfg):
    return {
        "disk": disk_report(cfg),
        "home_root": home_root_guard(),
        "dotfiles": dotfile_audit(),
        "python": util.which("python") or util.which("py"),
        "git": util.which("git"),
        "gh": util.which("gh"),
        "ipfs": util.which("ipfs"),
        "huggingface": util.which("huggingface-cli") or util.which("hf"),
    }
