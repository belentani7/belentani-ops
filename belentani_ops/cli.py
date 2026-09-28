import argparse
import json

from . import backup, github, llm, monitor, report, secrets, system, util
from .config import PROJECT_ROOT, load_config, save_config


def _load(args):
    cfg, source = load_config(getattr(args, "config", None))
    return cfg, source


def cmd_doctor(args):
    cfg, source = _load(args)
    util.head("Doctor")
    util.info(f"Config: {source if source else 'por defecto (sin archivo)'}")
    hc = system.healthcheck(cfg)
    for tool in ("python", "git", "gh", "ipfs", "huggingface"):
        if hc.get(tool):
            util.ok(f"{tool}: {hc[tool]}")
        else:
            util.warn(f"{tool}: no encontrado")
    disk_guard = system.disk_guard(cfg)
    util.info(f"Escritura permitida: {disk_guard['allowed']}")
    return 0


def cmd_system(args):
    cfg, _ = _load(args)
    if args.action == "disk":
        for row in system.disk_report(cfg):
            util.info(f"{row['drive']} libre {row['free_gb']}GB / total {util.human_bytes(row['total'])} [{row['level']}]")
    elif args.action == "home":
        findings = system.home_root_guard()
        util.head("Home root guard")
        if findings["stray_files"]:
            util.warn("Archivos/carpetas sueltos: " + ", ".join(findings["stray_files"][:40]))
        if findings["junk_dirs"]:
            util.err("Dotfiles basura: " + ", ".join(findings["junk_dirs"]))
        if findings["suspicious"]:
            util.warn("Dotfiles desconocidos: " + ", ".join(findings["suspicious"]))
        if not any(findings.values()):
            util.ok("Home root limpio")
    elif args.action == "dotfiles":
        data = system.dotfile_audit()
        util.info(f"Presentes: {len(data['present'])}")
        if data["junk"]:
            util.err("Basura: " + ", ".join(data["junk"]))
        if data["unknown"]:
            util.warn("Desconocidos: " + ", ".join(data["unknown"]))
    elif args.action == "processes":
        for row in system.top_processes(args.limit):
            util.info(f"{row['name']} (pid {row['pid']}): {util.human_bytes(row['mem'])}")
    elif args.action == "clean":
        plan = system.clean_plan(cfg)
        util.head("Plan de limpieza")
        total = 0
        for item in plan:
            total += item["size"]
            util.info(f"{util.human_bytes(item['size']):>10}  {item['files']:>7} files  {item['path']}")
        util.info(f"Total recuperable: {util.human_bytes(total)}")
        if args.apply:
            result = system.clean_apply(cfg, plan, assume_yes=args.yes)
            util.ok(f"Borrados {result['deleted']} elementos, liberados {util.human_bytes(result['freed'])}")
            for e in result["errors"][:10]:
                util.warn(e)
        else:
            util.info("Modo dry-run. Usa --apply para ejecutar.")
    elif args.action == "health":
        print(json.dumps(system.healthcheck(cfg), indent=2, ensure_ascii=False))
    return 0


def cmd_repos(args):
    cfg, _ = _load(args)
    if not github.gh_available():
        util.err("gh no esta en PATH")
        return 1
    if args.action == "list":
        repos, error = github.list_repos(cfg.github_user, args.limit)
        if error:
            util.err(error)
            return 1
        util.info(f"{len(repos)} repos")
        for r in repos:
            lang = r.get("primaryLanguage") or {}
            lang = lang.get("name", "") if isinstance(lang, dict) else str(lang)
            util.info(f"{r['name']:<45} {r.get('visibility',''):<8} {lang}")
    elif args.action == "audit":
        result = github.audit_repos(cfg.github_user, args.limit, deep=args.deep)
        if not result.get("ok"):
            util.err(result.get("error", "error"))
            return 1
        util.head("Auditoria de repos")
        stats = result["stats"]
        util.info(f"Total {stats['total']} | archived {stats['archived']} | forks {stats['forks']}")
        util.info(f"Sin descripcion {stats['no_description']} | sin LICENSE {stats['no_license']} | sin README {stats['no_readme']} | sin CI {stats['no_ci']}")
        for f in result["findings"][: args.limit]:
            util.warn(f"{f['repo']}: {', '.join(f['issues'])}")
    elif args.action == "pages":
        status = github.pages_status(f"{cfg.github_user}/{args.repo}")
        print(json.dumps(status, indent=2, ensure_ascii=False))
    elif args.action == "deploy":
        ok, detail = github.deploy_pages(f"{cfg.github_user}/{args.repo}", args.branch)
        (util.ok if ok else util.err)(detail)
        return 0 if ok else 1
    return 0


def cmd_secrets(args):
    cfg, _ = _load(args)
    if args.action == "scan":
        data = secrets.scan_report(cfg)
        util.head("Scan de secretos")
        util.info(f"Escaneados {data['scanned']} archivos")
        if data["truncated"]:
            util.warn("Scan truncado por limite de archivos")
        for hit in data["hits"][:60]:
            util.err(f"{hit['kind']}: {hit['masked']} -> {hit['file']}:{hit['line']}")
        if not data["hits"]:
            util.ok("Sin secretos detectados")
        if data["env_files"]:
            util.warn(f".env encontrados: {len(data['env_files'])}")
            for f in data["env_files"][:20]:
                util.info(f"  {f}")
    elif args.action == "rotation":
        util.head("Checklist de rotacion")
        for item in secrets.rotation_checklist():
            util.info("- " + item)
    elif args.action == "mask":
        util.info(util.mask(args.value, args.keep))
    return 0


def cmd_backup(args):
    cfg, _ = _load(args)
    if args.action == "plan":
        plan = backup.backup_plan(cfg)
        util.head("Plan de backup")
        for k, v in plan["tools"].items():
            util.info(f"{k}: {v or 'no encontrado'}")
        util.info(f"HF: {plan['hf']}")
        util.info(f"IPFS: {plan['ipfs']}")
        for r in plan["repos"]:
            util.info(f"{r['path']}: repo={r.get('is_repo')} dirty={r.get('dirty')} unpushed={r.get('unpushed')}")
    elif args.action == "run":
        result = backup.backup_run(cfg, push=not args.no_push, assume_yes=args.yes)
        if result.get("cancelled"):
            util.warn("Cancelado")
            return 0
        for r in result["results"]:
            if r.get("ok"):
                util.ok(f"{r['path']} {'(sin cambios)' if r.get('noop') else 'respaldado'}")
            else:
                util.err(f"{r['path']}: {r.get('error')}")
    return 0


def cmd_llm(args):
    cfg, _ = _load(args)
    if args.action == "providers":
        for row in llm.provider_status(cfg):
            mark = "key OK" if row["key_present"] else "sin key"
            util.info(f"{row['provider']:<20} {row['tier']:<8} {mark:<8} {row['key_env'] or ''}")
    elif args.action == "health":
        for row in llm.health(cfg):
            (util.ok if row["reachable"] else util.warn)(f"{row['provider']}: {row['status'] or row['error']}")
    elif args.action == "route":
        util.info(f"Tarea '{args.task}' -> {', '.join(llm.route(args.task, cfg))}")
        util.ok(f"Recomendado: {llm.pick(args.task, cfg)}")
    elif args.action == "costs":
        summary = llm.check_threshold(cfg, args.limit)
        util.head("Costes")
        util.info(f"Total ${summary['total_usd']} en {summary['records']} registros (limite ${summary['limit_usd']})")
        for k, v in summary["by_provider"].items():
            util.info(f"  {k}: ${v}")
        if summary["over_limit"]:
            util.err("LIMITE SUPERADO")
        if args.log:
            llm.log_cost(args.log[0], args.log[1], int(args.log[2]), int(args.log[3]), float(args.log[4]), args.log[5] if len(args.log) > 5 else "")
            util.ok("Coste registrado")
    return 0


def cmd_monitor(args):
    cfg, _ = _load(args)
    if args.urls:
        report_data = monitor.uptime_report(cfg, args.urls)
    else:
        report_data = monitor.monitor_and_alert(cfg)
    if args.json:
        print(json.dumps(report_data, indent=2, ensure_ascii=False))
    return 0


def cmd_report(args):
    cfg, _ = _load(args)
    data = report.full_report(cfg, deep=args.deep, include_scan=args.secrets, include_monitor=not args.no_monitor)
    report.print_summary(data)
    if args.out:
        path = report.write_report_json(data, args.out)
        util.ok(f"Informe escrito en {path}")
    return 0


def cmd_run(args):
    cfg, _ = _load(args)
    util.head("Cadena completa belentani-ops")
    data = report.full_report(cfg, deep=args.deep, include_scan=True, include_monitor=True)
    report.print_summary(data)
    out = args.out or str(PROJECT_ROOT / "reports" / f"report-{util.now_iso().replace(':','').replace('-','')}.json")
    path = report.write_report_json(data, out)
    util.ok(f"Informe completo en {path}")
    if args.backup:
        result = backup.backup_run(cfg, push=True, assume_yes=args.yes)
        util.info(f"Backup: {result}")
    return 0


def cmd_config(args):
    cfg, source = _load(args)
    if args.action == "show":
        print(json.dumps(cfg.to_dict(), indent=2, ensure_ascii=False))
    elif args.action == "init":
        target = args.path or str(PROJECT_ROOT / "belentani_ops.config.json")
        path = save_config(cfg, target)
        util.ok(f"Config escrito en {path}")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(prog="belentani-ops", description="Toolkit de operaciones del ecosistema Belentani")
    parser.add_argument("--config", help="ruta a config JSON")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("doctor", help="diagnostico del entorno")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("system", help="disco, home-guard, limpieza")
    p.add_argument("action", choices=["disk", "home", "dotfiles", "processes", "clean", "health"])
    p.add_argument("--apply", action="store_true")
    p.add_argument("--yes", action="store_true")
    p.add_argument("--limit", type=int, default=15)
    p.set_defaults(func=cmd_system)

    p = sub.add_parser("repos", help="github: listar, auditar, pages")
    p.add_argument("action", choices=["list", "audit", "pages", "deploy"])
    p.add_argument("--limit", type=int, default=100)
    p.add_argument("--deep", action="store_true")
    p.add_argument("--repo", default="")
    p.add_argument("--branch", default="main")
    p.set_defaults(func=cmd_repos)

    p = sub.add_parser("secrets", help="scan y rotacion de secretos")
    p.add_argument("action", choices=["scan", "rotation", "mask"])
    p.add_argument("--value", default="")
    p.add_argument("--keep", type=int, default=4)
    p.set_defaults(func=cmd_secrets)

    p = sub.add_parser("backup", help="backup git/hf/ipfs")
    p.add_argument("action", choices=["plan", "run"])
    p.add_argument("--no-push", action="store_true")
    p.add_argument("--yes", action="store_true")
    p.set_defaults(func=cmd_backup)

    p = sub.add_parser("llm", help="proveedores, rutas y costes")
    p.add_argument("action", choices=["providers", "health", "route", "costs"])
    p.add_argument("--task", default="coding")
    p.add_argument("--limit", type=float, default=20.0)
    p.add_argument("--log", nargs="*")
    p.set_defaults(func=cmd_llm)

    p = sub.add_parser("monitor", help="uptime de sitios")
    p.add_argument("--urls", nargs="*")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_monitor)

    p = sub.add_parser("report", help="informe agregado")
    p.add_argument("--deep", action="store_true")
    p.add_argument("--secrets", action="store_true")
    p.add_argument("--no-monitor", action="store_true")
    p.add_argument("--out", default="")
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("run", help="cadena completa")
    p.add_argument("--deep", action="store_true")
    p.add_argument("--backup", action="store_true")
    p.add_argument("--yes", action="store_true")
    p.add_argument("--out", default="")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("config", help="ver/inicializar config")
    p.add_argument("action", choices=["show", "init"])
    p.add_argument("--path", default="")
    p.set_defaults(func=cmd_config)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        util.warn("Interrumpido")
        return 130
