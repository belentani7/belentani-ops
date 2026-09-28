
from . import backup, github, llm, monitor, secrets, system, util


def full_report(cfg, deep=False, include_scan=False, include_monitor=True):
    report = {"ts": util.now_iso()}
    util.head("Estado del ecosistema Belentani")

    report["disk"] = system.disk_report(cfg)
    primary = next((r for r in report["disk"] if r["drive"].upper().startswith("C")), None)
    if primary:
        util.info(f"Disco {primary['drive']}: {primary['free_gb']}GB libres ({primary['level']})")

    home = system.home_root_guard()
    report["home_root"] = home
    if home["stray_files"]:
        util.warn(f"Home root con {len(home['stray_files'])} archivos sueltos")
    if home["junk_dirs"]:
        util.warn(f"Dotfiles basura: {', '.join(home['junk_dirs'])}")

    report["github"] = github.audit_repos(cfg.github_user, limit=300, deep=deep) if github.gh_available() else {"ok": False, "error": "gh no disponible"}

    report["backup"] = backup.backup_plan(cfg)

    report["llm"] = {
        "providers": llm.provider_status(cfg),
        "costs": llm.cost_summary(),
    }

    if include_monitor:
        report["monitor"] = monitor.uptime_report(cfg)

    if include_scan:
        report["secrets"] = secrets.scan_report(cfg)

    return report


def write_report_json(report, path):
    return util.write_json(path, report)


def print_summary(report):
    util.head("Resumen")
    gh = report.get("github", {})
    if gh.get("ok"):
        s = gh.get("stats", {})
        util.info(f"GitHub: {s.get('total',0)} repos | sin desc {s.get('no_description',0)} | stale {s.get('stale',0)}")
    else:
        util.warn(f"GitHub: {gh.get('error','no disponible')}")

    mon = report.get("monitor")
    if mon:
        util.info(f"Sitios: {mon['up']}/{mon['checked']} arriba")

    costs = report.get("llm", {}).get("costs", {})
    util.info(f"Coste registrado: ${costs.get('total_usd', 0)} en {costs.get('records', 0)} registros")

    if report.get("secrets"):
        hits = report["secrets"].get("hits", [])
        if hits:
            util.err(f"Secretos detectados: {len(hits)}")
        else:
            util.ok("Sin secretos detectados en el scan")
