from __future__ import annotations

import datetime as dt
import html
import json
import os
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlencode


USERNAME = os.environ.get("GITHUB_USERNAME", "TomLo-FStack")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
ROOT = Path(__file__).resolve().parents[1]
PROFILE_REPO = USERNAME
PREFERRED_REPOS = ["mojo-data-structures-50", "ds50-speedforge", "come-ds-cli-challenge"]

LANGUAGE_COLORS = {
    "Mojo": "ff4f2e",
    "V": "5d87bf",
    "C": "555555",
    "C++": "f34b7d",
    "Elixir": "6e4a7e",
    "Python": "3776ab",
    "Mixed": "64748b",
}


def github_json(url: str) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{USERNAME}-profile-readme-generator",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def public_repos() -> list[dict[str, Any]]:
    repos: list[dict[str, Any]] = []
    page = 1
    while True:
        url = (
            f"https://api.github.com/users/{USERNAME}/repos"
            f"?type=owner&sort=pushed&direction=desc&per_page=100&page={page}"
        )
        chunk = github_json(url)
        if not chunk:
            break
        repos.extend(chunk)
        page += 1
    return repos


def text(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    value = str(value).strip()
    return value if value else fallback


def language_name(repo: dict[str, Any]) -> str:
    language = repo.get("language")
    return text(language, "Mixed")


def escape(value: Any) -> str:
    return html.escape(text(value), quote=True)


def badge(label: str, message: str, color: str = "0f172a") -> str:
    params = urlencode(
        {
            "label": label,
            "message": message,
            "color": color,
            "style": "for-the-badge",
            "labelColor": "0b1020",
        }
    )
    return f"https://img.shields.io/static/v1?{params}"


def shorten(value: Any, limit: int) -> str:
    content = text(value)
    if len(content) <= limit:
        return content
    return content[: max(0, limit - 3)].rstrip() + "..."


def ordered_projects(repos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    preferred = [repo for name in PREFERRED_REPOS for repo in repos if repo["name"] == name]
    rest = [repo for repo in repos if repo["name"] not in PREFERRED_REPOS]
    return preferred + rest


def repo_line(repo: dict[str, Any]) -> str:
    name = repo["name"]
    url = repo["html_url"]
    desc = text(repo.get("description"), "No description yet.")
    language = language_name(repo)
    stars = repo.get("stargazers_count", 0)
    forks = repo.get("forks_count", 0)
    pushed = text(repo.get("pushed_at"), "")
    pushed_day = pushed[:10] if pushed else "unknown"
    fork_badge = " fork" if repo.get("fork") else ""
    return (
        f"- [{name}]({url})"
        f" - {desc}"
        f" | `{language}` | stars `{stars}` | forks `{forks}` | pushed `{pushed_day}`{fork_badge}"
    )


def repo_card(repo: dict[str, Any], width: str = "50%") -> str:
    name = escape(repo["name"])
    url = escape(repo["html_url"])
    desc = escape(text(repo.get("description"), "No description yet."))
    language = language_name(repo)
    color = LANGUAGE_COLORS.get(language, "64748b")
    stars = repo.get("stargazers_count", 0)
    forks = repo.get("forks_count", 0)
    pushed = text(repo.get("pushed_at"), "")[:10] or "unknown"
    fork_badge = " &nbsp; <code>fork</code>" if repo.get("fork") else ""
    return (
        f"<td width=\"{width}\" valign=\"top\">\n"
        f"<a href=\"{url}\"><strong>{name}</strong></a><br/>\n"
        f"<span>{desc}</span><br/><br/>\n"
        f"<img src=\"{badge('lang', language, color)}\" alt=\"{language}\" /> "
        f"<img src=\"{badge('stars', str(stars), 'f59e0b')}\" alt=\"stars {stars}\" /> "
        f"<img src=\"{badge('forks', str(forks), '38bdf8')}\" alt=\"forks {forks}\" /><br/>\n"
        f"<sub>last push: <code>{pushed}</code>{fork_badge}</sub>\n"
        "</td>"
    )


def spotlight(repos: list[dict[str, Any]]) -> str:
    if not repos:
        return ""

    primary = ordered_projects(repos)[0]
    return (
        "<table>\n<tr>\n"
        f"{repo_card(primary, '100%')}\n"
        "</tr>\n</table>"
    )


def project_table(repos: list[dict[str, Any]], skip_spotlight: bool = False) -> str:
    ordered = ordered_projects(repos)
    featured = [repo for repo in ordered if not repo.get("fork")]
    if skip_spotlight and len(featured) > 1:
        featured = featured[1:]
    featured = featured[:6]
    if not featured:
        featured = ordered[:6]

    cells: list[str] = []
    for repo in featured:
        cells.append(repo_card(repo))

    rows: list[str] = []
    for i in range(0, len(cells), 2):
        left = cells[i]
        right = cells[i + 1] if i + 1 < len(cells) else "<td width=\"50%\"></td>"
        rows.append(f"<tr>\n{left}\n{right}\n</tr>")
    return "<table>\n" + "\n".join(rows) + "\n</table>"


def language_bar(counter: Counter[str]) -> str:
    if not counter:
        return "`No language data yet.`"

    total = sum(counter.values())
    parts: list[str] = []
    for language, count in counter.most_common(8):
        pct = round(count * 100 / total)
        color = LANGUAGE_COLORS.get(language, "64748b")
        parts.append(f"<img src=\"{badge(language, str(pct) + '%', color)}\" alt=\"{language} {pct}%\" />")
    return "\n".join(parts)


def stack_badges() -> str:
    stack = [
        ("Mojo", "ff4f2e"),
        ("V", "5d87bf"),
        ("C", "555555"),
        ("C++", "f34b7d"),
        ("Elixir", "6e4a7e"),
        ("Python", "3776ab"),
        ("WSL2", "2563eb"),
        ("GitHub Actions", "2088ff"),
    ]
    return "\n".join(f"<img src=\"{badge('stack', name, color)}\" alt=\"{name}\" />" for name, color in stack)


def write_hero_svg(source_repos: list[dict[str, Any]], languages: Counter[str], updated: str) -> None:
    assets = ROOT / "assets"
    assets.mkdir(exist_ok=True)

    top_language = languages.most_common(1)[0][0] if languages else "Systems"
    lead_repo = next(
        (repo for repo in source_repos if repo["name"] == "mojo-data-structures-50"),
        source_repos[0] if source_repos else {},
    )
    lead_name = escape(text(lead_repo.get("name"), "mojo-data-structures-50"))
    lead_desc = escape(shorten(lead_repo.get("description"), 78) or "Mojo-first data-structure systems workbench.")
    repo_count = str(len(source_repos))
    lang_count = str(len(languages))

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="390" viewBox="0 0 1280 390" role="img" aria-label="Tom Lo systems forge banner">
  <defs>
    <linearGradient id="bg" x1="0" x2="1" y1="0" y2="1">
      <stop offset="0" stop-color="#04060d"/>
      <stop offset="0.48" stop-color="#0a1020"/>
      <stop offset="1" stop-color="#1a0615"/>
    </linearGradient>
    <linearGradient id="hot" x1="0" x2="1">
      <stop offset="0" stop-color="#facc15"/>
      <stop offset="0.5" stop-color="#22d3ee"/>
      <stop offset="1" stop-color="#ff2d95"/>
    </linearGradient>
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="4" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
    <pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse">
      <path d="M 32 0 L 0 0 0 32" fill="none" stroke="#1f2a44" stroke-width="1" opacity="0.55"/>
    </pattern>
    <pattern id="scan" width="8" height="8" patternUnits="userSpaceOnUse">
      <path d="M0 0H8" stroke="#ffffff" stroke-width="1" opacity="0.035"/>
    </pattern>
  </defs>

  <rect width="1280" height="390" fill="url(#bg)"/>
  <rect width="1280" height="390" fill="url(#grid)"/>
  <rect width="1280" height="390" fill="url(#scan)"/>
  <rect x="18" y="18" width="1244" height="354" fill="none" stroke="#22304e" stroke-width="2"/>
  <path d="M18 58H226L258 90H402" fill="none" stroke="#facc15" stroke-width="3"/>
  <path d="M862 18H1262V92H790Z" fill="#22d3ee" opacity="0.85"/>
  <path d="M995 260H1262V372H920Z" fill="#ff2d95" opacity="0.86"/>
  <path d="M18 292H360L440 372H18Z" fill="#facc15" opacity="0.96"/>
  <path d="M0 132H216L162 188H0Z" fill="#ff2d95" opacity="0.38"/>
  <path d="M486 0L604 0L247 390H128Z" fill="#111827" opacity="0.72"/>

  <g opacity="0.75">
    <path d="M742 50H838M742 74H808M742 98H858" stroke="#22d3ee" stroke-width="3"/>
    <path d="M1110 116H1226M1086 140H1194M1138 164H1262" stroke="#ff2d95" stroke-width="3"/>
    <path d="M620 300H740M650 324H800M690 348H770" stroke="#facc15" stroke-width="3"/>
  </g>

  <g transform="translate(64 68)">
    <text x="0" y="0" fill="#facc15" font-family="JetBrains Mono, Consolas, monospace" font-size="20" font-weight="800" letter-spacing="4">TOM LO / SYSTEMS FORGE</text>
    <text x="-4" y="72" fill="#22d3ee" opacity="0.55" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="62" font-weight="900">MOJO DATA</text>
    <text x="4" y="72" fill="#ff2d95" opacity="0.55" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="62" font-weight="900">MOJO DATA</text>
    <text x="0" y="72" fill="#f8fafc" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="62" font-weight="900">MOJO DATA</text>
    <text x="-4" y="136" fill="#22d3ee" opacity="0.5" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="62" font-weight="900">STRUCTURES 50</text>
    <text x="4" y="136" fill="#ff2d95" opacity="0.5" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="62" font-weight="900">STRUCTURES 50</text>
    <text x="0" y="136" fill="#f8fafc" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="62" font-weight="900">STRUCTURES 50</text>
    <rect x="0" y="162" width="690" height="4" fill="url(#hot)" filter="url(#glow)"/>
    <text x="0" y="204" fill="#e2e8f0" font-family="JetBrains Mono, Consolas, monospace" font-size="21">lead target :: {lead_name}</text>
    <text x="0" y="236" fill="#94a3b8" font-family="JetBrains Mono, Consolas, monospace" font-size="17">{lead_desc}</text>
  </g>

  <g transform="translate(810 122)">
    <rect x="0" y="0" width="380" height="145" rx="0" fill="#080d1a" stroke="#22d3ee" stroke-width="2"/>
    <path d="M0 0H118L154 34H380" fill="none" stroke="#facc15" stroke-width="4"/>
    <rect x="24" y="70" width="332" height="1" fill="#22304e"/>
    <text x="28" y="44" fill="#facc15" font-family="JetBrains Mono, Consolas, monospace" font-size="16" font-weight="800">RUNTIME HUD</text>
    <text x="222" y="44" fill="#22d3ee" font-family="JetBrains Mono, Consolas, monospace" font-size="13">{escape(top_language).upper()}</text>
    <text x="28" y="98" fill="#f8fafc" font-family="JetBrains Mono, Consolas, monospace" font-size="22">repos      {repo_count}</text>
    <text x="28" y="128" fill="#f8fafc" font-family="JetBrains Mono, Consolas, monospace" font-size="22">languages  {lang_count}</text>
  </g>

  <g transform="translate(64 318)">
    <rect x="0" y="-24" width="214" height="40" fill="#05070d" stroke="#facc15" stroke-width="2"/>
    <rect x="232" y="-24" width="238" height="40" fill="#05070d" stroke="#22d3ee" stroke-width="2"/>
    <rect x="488" y="-24" width="154" height="40" fill="#05070d" stroke="#ff2d95" stroke-width="2"/>
    <text x="18" y="2" fill="#facc15" font-family="JetBrains Mono, Consolas, monospace" font-size="16" font-weight="800">CORRECTNESS FIRST</text>
    <text x="250" y="2" fill="#22d3ee" font-family="JetBrains Mono, Consolas, monospace" font-size="16" font-weight="800">BENCHMARKS SECOND</text>
    <text x="514" y="2" fill="#ff2d95" font-family="JetBrains Mono, Consolas, monospace" font-size="16" font-weight="800">SHIP CLEAN</text>
  </g>

  <text x="1216" y="346" fill="#f8fafc" opacity="0.62" text-anchor="end" font-family="JetBrains Mono, Consolas, monospace" font-size="13">AUTO {escape(updated)}</text>
</svg>
"""
    (assets / "neon-forge.svg").write_text(svg, encoding="utf-8", newline="\n")


def write_signal_svg(
    source_repos: list[dict[str, Any]],
    languages: Counter[str],
    active_count: int,
    total_stars: int,
    total_forks: int,
    updated: str,
) -> None:
    assets = ROOT / "assets"
    assets.mkdir(exist_ok=True)

    top_language = languages.most_common(1)[0][0] if languages else "Systems"
    repo_count = str(len(source_repos))
    updated_label = escape(updated.replace(" UTC", "Z"))

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="92" viewBox="0 0 1280 92" role="img" aria-label="Tom Lo live build signal">
  <defs>
    <linearGradient id="rail" x1="0" x2="1">
      <stop offset="0" stop-color="#facc15"/>
      <stop offset="0.5" stop-color="#22d3ee"/>
      <stop offset="1" stop-color="#ff2d95"/>
    </linearGradient>
    <filter id="soft" x="-20%" y="-30%" width="140%" height="160%">
      <feGaussianBlur stdDeviation="3" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>
  <rect width="1280" height="92" fill="#05070d"/>
  <rect x="18" y="12" width="1244" height="68" fill="#080d1a" stroke="#22304e" stroke-width="2"/>
  <rect x="18" y="12" width="1244" height="3" fill="url(#rail)" filter="url(#soft)"/>
  <path d="M36 80H312L346 46H462" fill="none" stroke="#facc15" stroke-width="2"/>
  <path d="M1046 12H1262V80H1002Z" fill="#ff2d95" opacity="0.2"/>
  <text x="46" y="43" fill="#f8fafc" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="24" font-weight="800">Tom Lo // systems workbench</text>
  <text x="46" y="66" fill="#94a3b8" font-family="JetBrains Mono, Consolas, monospace" font-size="15">Mojo data structures, language experiments, benchmark tooling</text>

  <g font-family="JetBrains Mono, Consolas, monospace" font-weight="800" font-size="13">
    <text x="690" y="38" fill="#facc15">PROJECTS</text>
    <text x="690" y="62" fill="#f8fafc">{repo_count}</text>
    <text x="800" y="38" fill="#22d3ee">ACTIVE</text>
    <text x="800" y="62" fill="#f8fafc">{active_count}</text>
    <text x="900" y="38" fill="#ff2d95">LANG</text>
    <text x="900" y="62" fill="#f8fafc">{escape(top_language).upper()}</text>
    <text x="1018" y="38" fill="#facc15">STARS</text>
    <text x="1018" y="62" fill="#f8fafc">{total_stars}</text>
    <text x="1110" y="38" fill="#22d3ee">FORKS</text>
    <text x="1110" y="62" fill="#f8fafc">{total_forks}</text>
    <text x="1198" y="38" fill="#ff2d95" text-anchor="end">AUTO</text>
    <text x="1198" y="62" fill="#f8fafc" text-anchor="end">{updated_label}</text>
  </g>
</svg>
"""
    (assets / "signal-strip.svg").write_text(svg, encoding="utf-8", newline="\n")


def render(repos: list[dict[str, Any]], user: dict[str, Any]) -> str:
    public = [repo for repo in repos if not repo.get("private")]
    project_repos = [repo for repo in public if repo["name"] != PROFILE_REPO]
    source_repos = project_repos or public or repos
    non_fork_projects = [repo for repo in source_repos if not repo.get("fork")]
    languages = Counter(language_name(repo) for repo in source_repos)
    total_stars = sum(repo.get("stargazers_count", 0) for repo in source_repos)
    total_forks = sum(repo.get("forks_count", 0) for repo in source_repos)
    now = dt.datetime.now(dt.UTC)
    updated = now.strftime("%Y-%m-%d %H:%M UTC")
    badge_updated = now.strftime("%Y.%m.%d %H:%M UTC")
    write_hero_svg(source_repos, languages, updated)
    write_signal_svg(source_repos, languages, len(non_fork_projects), total_stars, total_forks, updated)
    bio = text(user.get("bio"), "Systems builder focused on data structures, language experiments, and fast tooling.")

    recent = "\n".join(repo_line(repo) for repo in source_repos[:8])
    if not recent:
        recent = "- Building in public soon."

    return f"""<!-- AUTO-GENERATED by scripts/build_readme.py. Edit the script, not this file. -->

<p align="center">
  <img width="100%" src="./assets/neon-forge.svg" alt="Tom Lo systems forge banner" />
</p>

<p align="center">
  <img width="100%" src="./assets/signal-strip.svg" alt="Tom Lo live build signal" />
</p>

<p align="center">
  <a href="https://github.com/{USERNAME}?tab=repositories"><img alt="Projects" src="{badge('projects', str(len(source_repos)), '0f172a')}"></a>
  <img alt="Active builds" src="{badge('active builds', str(len(non_fork_projects)), '7c3aed')}">
  <img alt="Stars" src="{badge('stars', str(total_stars), 'f59e0b')}">
  <img alt="Forks" src="{badge('forks', str(total_forks), '38bdf8')}">
  <img alt="Updated" src="{badge('auto update', badge_updated, '22c55e')}">
</p>

## Main Signal

{spotlight(source_repos)}

## Mission Control

{bio}

I like projects where correctness and speed can both be inspected: data-structure workloads, language runtimes, CLI drills, and benchmark harnesses.

```text
vector :: Mojo DS50 + speed drills
style  :: compact APIs + smoke tests
mode   :: measure, clean, ship
```

## Project Radar

{project_table(source_repos, skip_spotlight=True)}

## Toolchain

<p align="center">
{stack_badges()}
</p>

## Language Signal

<p align="center">
{language_bar(languages)}
</p>

## Live Telemetry

<p align="center">
  <img height="165" src="https://github-readme-stats.vercel.app/api?username={USERNAME}&show_icons=true&theme=tokyonight&hide_border=true&include_all_commits=true&rank_icon=github" alt="GitHub stats" />
  <img height="165" src="https://github-readme-stats.vercel.app/api/top-langs/?username={USERNAME}&layout=compact&theme=tokyonight&hide_border=true&langs_count=8" alt="Top languages" />
</p>

<p align="center">
  <img src="https://github-profile-trophy.vercel.app/?username={USERNAME}&theme=tokyonight&no-frame=true&no-bg=true&margin-w=8&row=1" alt="GitHub trophies" />
</p>

<p align="center">
  <img src="https://github-readme-activity-graph.vercel.app/graph?username={USERNAME}&theme=tokyo-night&hide_border=true&area=true" alt="Contribution activity graph" />
</p>

## Latest Public Pushes

{recent}

## Automation

This profile README updates itself from GitHub Actions. The workflow reads public repository metadata, rebuilds this page, and commits the diff when anything changes.

<sub>Last generated: {updated}</sub>
"""


def main() -> None:
    user = github_json(f"https://api.github.com/users/{USERNAME}")
    repos = public_repos()
    (ROOT / "README.md").write_text(render(repos, user), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
