import json

from . import util


def gh_available():
    return util.which("gh") is not None


def gh_auth_status():
    code, out, errout = util.run(["gh", "auth", "status"], timeout=30)
    return code == 0, util.truncate(out + errout, 1500)


def list_repos(user=None, limit=300):
    user = user or "belentani7"
    code, out, errout = util.run(
        ["gh", "repo", "list", user, "--limit", str(limit),
         "--json", "name,description,visibility,isFork,isArchived,"
                   "primaryLanguage,stargazerCount,updatedAt,url,hasIssuesEnabled"],
        timeout=120,
    )
    if code != 0:
        return [], errout
    try:
        return json.loads(out), ""
    except Exception as exc:
        return [], str(exc)


def repo_detail(full):
    code, out, errout = util.run(
        ["gh", "repo", "view", full, "--json",
         "name,description,licenseInfo,repositoryTopics,defaultBranchRef,languages,url,homepageUrl"],
        timeout=60,
    )
    if code != 0:
        return None, errout
    try:
        return json.loads(out), ""
    except Exception as exc:
        return None, str(exc)


def has_file(full, path):
    code, out, _ = util.run(
        ["gh", "api", f"repos/{full}/contents/{path}", "--jq", ".name"],
        timeout=30,
    )
    return code == 0 and out.strip() != ""


def pages_status(full):
    code, out, errout = util.run(
        ["gh", "api", f"repos/{full}/pages", "--jq", ".status, .html_url"],
        timeout=30,
    )
    if code != 0:
        return {"enabled": False, "error": errout.strip()}
    parts = [p for p in out.strip().splitlines() if p]
    return {"enabled": True, "status": parts[0] if parts else "", "url": parts[1] if len(parts) > 1 else ""}


def deploy_pages(full, branch="main", path="/"):
    code, out, errout = util.run(
        ["gh", "api", f"repos/{full}/pages", "-X", "POST",
         "-f", f"source[branch]={branch}", "-f", f"source[path]={path}"],
        timeout=60,
    )
    return code == 0, util.truncate(out + errout, 800)


def audit_repos(user=None, limit=100, deep=False):
    user = user or "belentani7"
    repos, error = list_repos(user, limit)
    if error:
        return {"ok": False, "error": error, "repos": [], "findings": []}
    findings = []
    stats = {"total": 0, "archived": 0, "forks": 0, "no_description": 0,
             "no_license": 0, "no_readme": 0, "no_ci": 0, "stale": 0}
    for repo in repos:
        stats["total"] += 1
        full = f"{user}/{repo['name']}"
        issues = []
        if repo.get("isArchived"):
            stats["archived"] += 1
        if repo.get("isFork"):
            stats["forks"] += 1
        if not repo.get("description"):
            stats["no_description"] += 1
            issues.append("sin descripcion")
        if deep and not repo.get("isArchived"):
            if not has_file(full, "LICENSE"):
                stats["no_license"] += 1
                issues.append("sin LICENSE")
            readme = any(has_file(full, n) for n in ("README.md", "readme.md", "README.rst"))
            if not readme:
                stats["no_readme"] += 1
                issues.append("sin README")
            workflows = has_file(full, ".github/workflows")
            if not workflows:
                stats["no_ci"] += 1
                issues.append("sin CI")
        if issues:
            findings.append({"repo": full, "url": repo.get("url"), "issues": issues})
    return {"ok": True, "stats": stats, "findings": findings, "repos": repos}


def open_sanitize_issue(full, issues):
    body = "Detectado por belentani-ops:\n\n" + "\n".join(f"- {i}" for i in issues)
    code, out, errout = util.run(
        ["gh", "issue", "create", "--repo", full,
         "--title", "chore: saneamiento de repo",
         "--body", body],
        timeout=60,
    )
    return code == 0, util.truncate(out + errout, 500)


def summary_line():
    authed, detail = gh_auth_status()
    if not authed:
        return f"gh no autenticado: {detail[:120]}"
    return "gh autenticado"
