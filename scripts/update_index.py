#!/usr/bin/env python3
"""
Rebuilds the APK index in README.md: finds every public andrejristic repository that
has GitHub Releases with .apk files and writes links to them between the
APK-INDEX markers. Only the standard library is used.

  GITHUB_TOKEN (optional) raises the API rate limit; in Actions it is provided.
"""
import json
import os
import re
import sys
import urllib.request

OWNER = "andrejristic"
SELF = "APK"
README = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "README.md")
START, END = "<!-- APK-INDEX:START -->", "<!-- APK-INDEX:END -->"


def api(path):
    req = urllib.request.Request("https://api.github.com" + path, headers={
        "Accept": "application/vnd.github+json", "User-Agent": "apk-index"})
    tok = os.environ.get("GITHUB_TOKEN")
    if tok:
        req.add_header("Authorization", f"Bearer {tok}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def mb(n):
    return f"{n / 1024 / 1024:.1f} MB"


def collect():
    repos, page = [], 1
    while True:
        batch = api(f"/users/{OWNER}/repos?type=owner&per_page=100&page={page}")
        repos += batch
        if len(batch) < 100:
            break
        page += 1
    apps = []
    for repo in sorted(repos, key=lambda r: r["name"].lower()):
        if repo["fork"] or repo["private"] or repo["archived"] or repo["name"] == SELF:
            continue
        rels = [r for r in api(f"/repos/{OWNER}/{repo['name']}/releases?per_page=50") if not r["draft"]]
        builds = []
        for rel in rels:
            for a in rel["assets"]:
                if a["name"].lower().endswith(".apk"):
                    builds.append({
                        "tag": rel["tag_name"], "pre": rel["prerelease"], "date": rel["published_at"][:10],
                        "name": a["name"], "url": a["browser_download_url"], "size": a["size"],
                        "page": rel["html_url"],
                    })
        if builds:
            apps.append({"repo": repo["name"], "desc": repo.get("description") or "",
                         "url": repo["html_url"], "builds": builds})
    return apps


def render(apps):
    if not apps:
        return "_Još nema objavljenih APK fajlova. · No APKs published yet._"
    lines = [
        "| Aplikacija · App | Verzija · Version | Datum · Date | Preuzmi · Download |",
        "|---|---|---|---|",
    ]
    for app in apps:
        stable = next((b for b in app["builds"] if not b["pre"]), None)
        test = next((b for b in app["builds"] if b["pre"]), None)
        cell = []
        if stable:
            cell.append(f"[**{stable['name']}**]({stable['url']}) ({mb(stable['size'])})")
        if test and (not stable or test["date"] >= stable["date"]):
            cell.append(f"test: [{test['name']}]({test['url']})")
        main = stable or test
        desc = f"<br><sub>{app['desc']}</sub>" if app["desc"] else ""
        lines.append(f"| [{app['repo']}]({app['url']}){desc} | {main['tag']} | {main['date']} | {'<br>'.join(cell)} |")
    lines += ["", "<details><summary>Sve verzije · All builds</summary>", ""]
    for app in apps:
        lines.append(f"**{app['repo']}**")
        lines.append("")
        for b in app["builds"]:
            tag = " _(test)_" if b["pre"] else ""
            lines.append(f"- [{b['name']}]({b['url']}) · {b['tag']}{tag} · {b['date']} · {mb(b['size'])}")
        lines.append("")
    lines.append("</details>")
    return "\n".join(lines)


def main():
    text = open(README, encoding="utf-8").read()
    if START not in text or END not in text:
        sys.exit("README is missing the APK-INDEX markers")
    block = render(collect())
    new = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: f"{START}\n{block}\n{END}", text, flags=re.S)
    if new != text:
        open(README, "w", encoding="utf-8").write(new)
        print("README updated")
    else:
        print("no change")


if __name__ == "__main__":
    main()
