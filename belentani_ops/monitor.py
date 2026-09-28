import json
import time
import urllib.error
import urllib.request

from . import util


def check_url(url, timeout=20):
    start = time.time()
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "belentani-ops/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(2048)
            elapsed = time.time() - start
            return {
                "url": url, "ok": 200 <= resp.status < 400, "status": resp.status,
                "ms": round(elapsed * 1000), "bytes_sampled": len(body),
            }
    except urllib.error.HTTPError as exc:
        return {"url": url, "ok": False, "status": exc.code, "ms": round((time.time() - start) * 1000), "error": "http error"}
    except Exception as exc:
        return {"url": url, "ok": False, "status": None, "ms": round((time.time() - start) * 1000), "error": str(exc)[:160]}


def check_sites(cfg, urls=None):
    targets = urls or cfg.sites
    return [check_url(u, cfg.monitor_timeout) for u in targets]


def uptime_report(cfg, urls=None):
    results = check_sites(cfg, urls)
    down = [r for r in results if not r["ok"]]
    return {
        "checked": len(results),
        "up": len(results) - len(down),
        "down": len(down),
        "results": results,
        "down_urls": [r["url"] for r in down],
    }


def send_alert(cfg, message):
    if not cfg.alert_webhook:
        return {"sent": False, "detail": "sin webhook configurado"}
    payload = json.dumps({"text": message}).encode("utf-8")
    req = urllib.request.Request(
        cfg.alert_webhook, data=payload, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return {"sent": True, "status": resp.status}
    except Exception as exc:
        return {"sent": False, "detail": str(exc)[:200]}


def monitor_and_alert(cfg, urls=None):
    report = uptime_report(cfg, urls)
    if report["down"] > 0:
        msg = "BELENTANI OPS: caidos " + ", ".join(report["down_urls"])
        report["alert"] = send_alert(cfg, msg)
        util.warn(f"{report['down']} sitio(s) caido(s)")
        for url in report["down_urls"]:
            util.err(f"  caido: {url}")
    else:
        util.ok(f"{report['up']}/{report['checked']} sitios arriba")
    return report
