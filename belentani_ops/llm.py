import json
import os
import urllib.error
import urllib.request

from . import util
from .config import HOME, TASK_ROUTES


def _key(provider_cfg):
    env_name = provider_cfg.get("key_env")
    if not env_name:
        return None, False
    val = os.environ.get(env_name)
    return val, bool(val)


def provider_status(cfg):
    rows = []
    for name, pcfg in cfg.providers.items():
        key, present = _key(pcfg)
        rows.append({
            "provider": name,
            "base_url": pcfg.get("base_url"),
            "tier": pcfg.get("tier"),
            "key_env": pcfg.get("key_env"),
            "key_present": present,
            "key_masked": util.mask(key) if key else "",
        })
    return rows


def ping(url, timeout=6):
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return {"ok": True, "status": resp.status}
    except urllib.error.HTTPError as exc:
        return {"ok": exc.code < 500, "status": exc.code}
    except Exception as exc:
        return {"ok": False, "status": None, "error": str(exc)[:160]}


def health(cfg):
    rows = []
    for name, pcfg in cfg.providers.items():
        base = pcfg.get("base_url", "")
        result = ping(base)
        rows.append({
            "provider": name,
            "reachable": result.get("ok", False),
            "status": result.get("status"),
            "error": result.get("error", ""),
        })
    return rows


def route(task="coding", cfg=None):
    chain = TASK_ROUTES.get(task, TASK_ROUTES["coding"])
    if cfg is None:
        return chain
    order = []
    for name in chain:
        if name in cfg.providers:
            order.append(name)
    return order


def pick(task="coding", cfg=None):
    for name in route(task, cfg):
        if cfg is None:
            return name
        pcfg = cfg.providers[name]
        _key_val, present = _key(pcfg)
        if pcfg.get("tier") in ("local", "free") or present:
            return name
    return route(task, cfg)[0] if route(task, cfg) else None


def cost_log_path():
    return HOME / ".belentani" / "ops" / "costs.jsonl"


def log_cost(provider, model, tokens_in, tokens_out, cost_usd, task=""):
    return util.append_jsonl(cost_log_path(), {
        "ts": util.now_iso(), "provider": provider, "model": model,
        "tokens_in": tokens_in, "tokens_out": tokens_out,
        "cost_usd": round(float(cost_usd), 6), "task": task,
    })


def cost_summary():
    records = []
    p = cost_log_path()
    if p.is_file():
        for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            try:
                records.append(json.loads(line))
            except Exception:
                continue
    by_provider = {}
    by_task = {}
    total = 0.0
    for r in records:
        total += r.get("cost_usd", 0)
        by_provider[r.get("provider", "?")] = by_provider.get(r.get("provider", "?"), 0) + r.get("cost_usd", 0)
        by_task[r.get("task", "?")] = by_task.get(r.get("task", "?"), 0) + r.get("cost_usd", 0)
    return {
        "records": len(records),
        "total_usd": round(total, 4),
        "by_provider": {k: round(v, 4) for k, v in by_provider.items()},
        "by_task": {k: round(v, 4) for k, v in by_task.items()},
    }


def check_threshold(cfg, limit_usd=None):
    summary = cost_summary()
    limit = limit_usd if limit_usd is not None else 20.0
    summary["limit_usd"] = limit
    summary["over_limit"] = summary["total_usd"] > limit
    return summary
