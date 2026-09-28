from pathlib import Path

from . import util


def tool_status():
    return {
        "git": util.which("git"),
        "gh": util.which("gh"),
        "huggingface-cli": util.which("huggingface-cli") or util.which("hf"),
        "ipfs": util.which("ipfs"),
    }


def git_status(repo_path):
    p = Path(repo_path)
    if not (p / ".git").exists():
        return {"path": str(p), "is_repo": False}
    code, out, _ = util.run(["git", "status", "--porcelain"], cwd=p, timeout=60)
    code2, branch, _ = util.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=p, timeout=30)
    code3, remote, _ = util.run(["git", "remote", "get-url", "origin"], cwd=p, timeout=30)
    code4, ahead, _ = util.run(["git", "rev-list", "--count", "@{u}..HEAD"], cwd=p, timeout=30)
    return {
        "path": str(p), "is_repo": True,
        "dirty": bool(out.strip()), "changes": len(out.strip().splitlines()),
        "branch": branch.strip() if code2 == 0 else "",
        "remote": remote.strip() if code3 == 0 else "",
        "unpushed": int(ahead.strip()) if code4 == 0 and ahead.strip().isdigit() else 0,
    }


def git_backup(repo_path, message=None, push=True, assume_yes=False):
    p = Path(repo_path)
    status = git_status(p)
    if not status.get("is_repo"):
        return {"path": str(p), "ok": False, "error": "no es repo git"}
    if not status["dirty"] and status["unpushed"] == 0:
        return {"path": str(p), "ok": True, "noop": True, "detail": "nada que respaldar"}
    msg = message or f"chore(backup): respaldo automatico {util.now_iso()}"
    util.run(["git", "add", "-A"], cwd=p, timeout=300)
    code, out, errout = util.run(["git", "commit", "-m", msg], cwd=p, timeout=300)
    if code != 0 and "nothing to commit" not in (out + errout):
        return {"path": str(p), "ok": False, "error": util.truncate(errout or out, 400)}
    if push:
        code, out, errout = util.run(["git", "push"], cwd=p, timeout=600)
        if code != 0:
            return {"path": str(p), "ok": False, "error": util.truncate(errout or out, 400)}
    return {"path": str(p), "ok": True, "pushed": push}


def hf_upload_check():
    cli = util.which("huggingface-cli") or util.which("hf")
    if not cli:
        return {"available": False, "detail": "huggingface-cli no instalado"}
    code, out, errout = util.run([cli, "whoami"], timeout=60)
    if code != 0:
        return {"available": True, "authed": False, "detail": util.truncate(errout, 300)}
    return {"available": True, "authed": True, "user": out.strip()}


def ipfs_check():
    cli = util.which("ipfs")
    if not cli:
        return {"available": False, "detail": "ipfs no instalado"}
    code, out, _ = util.run(["ipfs", "id", "-f", "<id>"], timeout=30)
    if code != 0:
        return {"available": True, "running": False}
    return {"available": True, "running": True, "id": out.strip()}


def backup_plan(cfg):
    plan = {"repos": [], "tools": tool_status(), "hf": hf_upload_check(), "ipfs": ipfs_check()}
    for repo in cfg.backup_repos:
        plan["repos"].append(git_status(repo))
    return plan


def backup_run(cfg, push=True, assume_yes=False):
    if not util.confirm("Ejecutar backup de repos git?", assume_yes):
        return {"cancelled": True}
    results = []
    for repo in cfg.backup_repos:
        results.append(git_backup(repo, push=push))
    return {"results": results}
