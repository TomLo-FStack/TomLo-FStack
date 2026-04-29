from __future__ import annotations

import datetime as dt
import html
import json
import os
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import urlencode


USERNAME = os.environ.get("GITHUB_USERNAME", "TomLo-FStack")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
SNAPSHOT_PATH = ASSETS / "language-stats.json"
PROFILE_REPO = USERNAME

LANGUAGE_COLORS = {
    "C": "555555",
    "C++": "f34b7d",
    "CSS": "563d7c",
    "Dockerfile": "384d54",
    "Elixir": "6e4a7e",
    "Go": "00add8",
    "HTML": "e34c26",
    "JavaScript": "f1e05a",
    "Julia": "a270ba",
    "Mojo": "ff4f2e",
    "PowerShell": "012456",
    "Python": "3776ab",
    "Shell": "89e051",
    "TypeScript": "3178c6",
    "V": "5d87bf",
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


def escape(value: Any) -> str:
    return html.escape(text(value), quote=True)


def language_name(repo: dict[str, Any]) -> str:
    return text(repo.get("language"), "Mixed")


def language_color(language: str) -> str:
    return LANGUAGE_COLORS.get(language, "64748b")


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


def format_bytes(value: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    size = float(value)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{value} B"


def load_language_snapshot() -> dict[str, Any]:
    if not SNAPSHOT_PATH.exists():
        return {}
    try:
        return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def previous_language_names(snapshot: dict[str, Any]) -> set[str]:
    languages = snapshot.get("languages", [])
    if not isinstance(languages, list):
        return set()
    return {text(item.get("name")) for item in languages if isinstance(item, dict) and text(item.get("name"))}


def repo_language_bytes(repo: dict[str, Any]) -> dict[str, int]:
    try:
        data = github_json(repo["languages_url"])
    except (KeyError, urllib.error.URLError, TimeoutError):
        data = {}

    if isinstance(data, dict) and data:
        return {str(language): int(size) for language, size in data.items() if int(size) > 0}

    language = language_name(repo)
    return {language: 1} if language != "Mixed" else {}


def collect_language_stats(
    repos: list[dict[str, Any]],
    previous_snapshot: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    bytes_by_language: Counter[str] = Counter()
    repos_by_language: dict[str, set[str]] = defaultdict(set)

    for repo in repos:
        languages = repo_language_bytes(repo)
        for language, byte_count in languages.items():
            bytes_by_language[language] += byte_count
            repos_by_language[language].add(repo["name"])

    total_bytes = sum(bytes_by_language.values())
    rows: list[dict[str, Any]] = []
    for language, byte_count in bytes_by_language.most_common():
        percent = round(byte_count * 100 / total_bytes, 1) if total_bytes else 0
        rows.append(
            {
                "name": language,
                "bytes": byte_count,
                "percent": percent,
                "repos": sorted(repos_by_language[language]),
                "color": language_color(language),
            }
        )

    previous = previous_language_names(previous_snapshot)
    current = {row["name"] for row in rows}
    baseline = not previous
    new_languages = sorted(current if baseline else current - previous)

    return {
        "generated_at": generated_at,
        "repo_count": len(repos),
        "total_bytes": total_bytes,
        "baseline": baseline,
        "new_languages": new_languages,
        "languages": rows,
    }


def write_language_snapshot(stats: dict[str, Any]) -> None:
    ASSETS.mkdir(exist_ok=True)
    SNAPSHOT_PATH.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


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
    stars = repo.get("stargazers_count", 0)
    forks = repo.get("forks_count", 0)
    pushed = text(repo.get("pushed_at"), "")[:10] or "unknown"
    fork_badge = " &nbsp; <code>fork</code>" if repo.get("fork") else ""
    return (
        f"<td width=\"{width}\" valign=\"top\">\n"
        f"<a href=\"{url}\"><strong>{name}</strong></a><br/>\n"
        f"<span>{desc}</span><br/><br/>\n"
        f"<img src=\"{badge('lang', language, language_color(language))}\" alt=\"{language}\" /> "
        f"<img src=\"{badge('stars', str(stars), 'f59e0b')}\" alt=\"stars {stars}\" /> "
        f"<img src=\"{badge('forks', str(forks), '38bdf8')}\" alt=\"forks {forks}\" /><br/>\n"
        f"<sub>last push: <code>{pushed}</code>{fork_badge}</sub>\n"
        "</td>"
    )


def project_table(repos: list[dict[str, Any]]) -> str:
    featured = [repo for repo in repos if not repo.get("fork")][:6] or repos[:6]

    cells = [repo_card(repo) for repo in featured]
    rows: list[str] = []
    for i in range(0, len(cells), 2):
        left = cells[i]
        right = cells[i + 1] if i + 1 < len(cells) else "<td width=\"50%\"></td>"
        rows.append(f"<tr>\n{left}\n{right}\n</tr>")
    return "<table>\n" + "\n".join(rows) + "\n</table>"


def language_badges(stats: dict[str, Any], limit: int = 8) -> str:
    languages = stats.get("languages", [])[:limit]
    if not languages:
        return "`No language data yet.`"
    return "\n".join(
        f"<img src=\"{badge(row['name'], f'{row['percent']:.1f}%', row['color'])}\" "
        f"alt=\"{escape(row['name'])} {row['percent']:.1f}%\" />"
        for row in languages
    )


def language_matrix(stats: dict[str, Any], limit: int = 8) -> str:
    languages = stats.get("languages", [])[:limit]
    if not languages:
        return "`No language data yet.`"

    rows = []
    for row in languages:
        repos = ", ".join(row["repos"][:4])
        if len(row["repos"]) > 4:
            repos += f", +{len(row['repos']) - 4}"
        rows.append(
            "| "
            f"`{escape(row['name'])}` "
            f"| `{row['percent']:.1f}%` "
            f"| `{format_bytes(row['bytes'])}` "
            f"| {escape(repos)} |"
        )

    return "\n".join(
        [
            "| Language | Share | Bytes | Seen in repos |",
            "| --- | ---: | ---: | --- |",
            *rows,
        ]
    )


def new_language_line(stats: dict[str, Any]) -> str:
    new_languages = stats.get("new_languages", [])
    if stats.get("baseline"):
        label = "Baseline scan"
    elif new_languages:
        label = "New since last daily scan"
    else:
        return "No new languages since the last daily scan."

    items = " ".join(
        f"<img src=\"{badge('new', language, language_color(language))}\" alt=\"new {escape(language)}\" />"
        for language in new_languages[:8]
    )
    if len(new_languages) > 8:
        items += f" <sub>+{len(new_languages) - 8} more</sub>"
    return f"{label}: {items}"


def stack_badges(stats: dict[str, Any]) -> str:
    languages = [(row["name"], row["color"]) for row in stats.get("languages", [])[:8]]
    tools = [("WSL2", "2563eb"), ("GitHub Actions", "2088ff")]
    return "\n".join(
        f"<img src=\"{badge('stack', name, color)}\" alt=\"{escape(name)}\" />"
        for name, color in [*languages, *tools]
    )


def write_hero_svg(stats: dict[str, Any], updated: str) -> None:
    ASSETS.mkdir(exist_ok=True)
    languages = stats.get("languages", [])
    top = languages[0] if languages else {"name": "Systems", "percent": 0, "color": "22d3ee"}
    second = languages[1] if len(languages) > 1 else top
    third = languages[2] if len(languages) > 2 else second
    lang_count = str(len(languages))
    repo_count = str(stats.get("repo_count", 0))
    byte_total = format_bytes(int(stats.get("total_bytes", 0)))
    top_line = " / ".join(row["name"].upper() for row in languages[:4]) or "SYSTEMS"

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="390" viewBox="0 0 1280 390" role="img" aria-label="Tom Lo polyglot systems data scientist banner">
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
    <text x="0" y="0" fill="#facc15" font-family="JetBrains Mono, Consolas, monospace" font-size="20" font-weight="800" letter-spacing="4">TOM LO / SYSTEMS DATA SCIENCE</text>
    <text x="-4" y="72" fill="#22d3ee" opacity="0.55" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="62" font-weight="900">POLYGLOT</text>
    <text x="4" y="72" fill="#ff2d95" opacity="0.55" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="62" font-weight="900">POLYGLOT</text>
    <text x="0" y="72" fill="#f8fafc" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="62" font-weight="900">POLYGLOT</text>
    <text x="-4" y="136" fill="#22d3ee" opacity="0.5" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="56" font-weight="900">SYSTEMS SCIENTIST</text>
    <text x="4" y="136" fill="#ff2d95" opacity="0.5" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="56" font-weight="900">SYSTEMS SCIENTIST</text>
    <text x="0" y="136" fill="#f8fafc" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="56" font-weight="900">SYSTEMS SCIENTIST</text>
    <rect x="0" y="162" width="690" height="4" fill="url(#hot)" filter="url(#glow)"/>
    <text x="0" y="204" fill="#e2e8f0" font-family="JetBrains Mono, Consolas, monospace" font-size="21">tracked stack :: {escape(top_line)}</text>
    <text x="0" y="236" fill="#94a3b8" font-family="JetBrains Mono, Consolas, monospace" font-size="17">systems-level data + computer science across public projects</text>
  </g>

  <g transform="translate(810 122)">
    <rect x="0" y="0" width="380" height="145" rx="0" fill="#080d1a" stroke="#22d3ee" stroke-width="2"/>
    <path d="M0 0H118L154 34H380" fill="none" stroke="#facc15" stroke-width="4"/>
    <rect x="24" y="70" width="332" height="1" fill="#22304e"/>
    <text x="28" y="44" fill="#facc15" font-family="JetBrains Mono, Consolas, monospace" font-size="16" font-weight="800">RESEARCH HUD</text>
    <text x="222" y="44" fill="#22d3ee" font-family="JetBrains Mono, Consolas, monospace" font-size="13">{escape(top['name']).upper()} {top['percent']:.1f}%</text>
    <text x="28" y="98" fill="#f8fafc" font-family="JetBrains Mono, Consolas, monospace" font-size="22">scanned    {repo_count}</text>
    <text x="28" y="128" fill="#f8fafc" font-family="JetBrains Mono, Consolas, monospace" font-size="22">languages  {lang_count}</text>
  </g>

  <g transform="translate(64 318)">
    <rect x="0" y="-24" width="202" height="40" fill="#05070d" stroke="#facc15" stroke-width="2"/>
    <rect x="220" y="-24" width="212" height="40" fill="#05070d" stroke="#22d3ee" stroke-width="2"/>
    <rect x="450" y="-24" width="212" height="40" fill="#05070d" stroke="#ff2d95" stroke-width="2"/>
    <text x="18" y="2" fill="#facc15" font-family="JetBrains Mono, Consolas, monospace" font-size="16" font-weight="800">{escape(top['name']).upper()} {top['percent']:.1f}%</text>
    <text x="238" y="2" fill="#22d3ee" font-family="JetBrains Mono, Consolas, monospace" font-size="16" font-weight="800">{escape(second['name']).upper()} {second['percent']:.1f}%</text>
    <text x="468" y="2" fill="#ff2d95" font-family="JetBrains Mono, Consolas, monospace" font-size="16" font-weight="800">{escape(third['name']).upper()} {third['percent']:.1f}%</text>
  </g>

  <text x="1216" y="346" fill="#f8fafc" opacity="0.62" text-anchor="end" font-family="JetBrains Mono, Consolas, monospace" font-size="13">BYTES {escape(byte_total)} / AUTO {escape(updated)}</text>
</svg>
"""
    (ASSETS / "neon-forge.svg").write_text(svg, encoding="utf-8", newline="\n")


def write_signal_svg(
    stats: dict[str, Any],
    active_count: int,
    total_stars: int,
    total_forks: int,
    updated: str,
) -> None:
    ASSETS.mkdir(exist_ok=True)
    languages = stats.get("languages", [])
    top_language = languages[0]["name"] if languages else "Systems"
    top_percent = languages[0]["percent"] if languages else 0
    new_count = len(stats.get("new_languages", []))
    repo_count = str(stats.get("repo_count", 0))
    updated_label = escape(updated.replace(" UTC", "Z"))

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="92" viewBox="0 0 1280 92" role="img" aria-label="Tom Lo language telemetry strip">
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
  <text x="46" y="43" fill="#f8fafc" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="24" font-weight="800">Tom Lo // polyglot systems/data scientist</text>
  <text x="46" y="66" fill="#94a3b8" font-family="JetBrains Mono, Consolas, monospace" font-size="15">multi-disciplinary programmer, byte-weighted language telemetry</text>

  <g font-family="JetBrains Mono, Consolas, monospace" font-weight="800" font-size="13">
    <text x="690" y="38" fill="#facc15">SCANNED</text>
    <text x="690" y="62" fill="#f8fafc">{repo_count}</text>
    <text x="800" y="38" fill="#22d3ee">ACTIVE</text>
    <text x="800" y="62" fill="#f8fafc">{active_count}</text>
    <text x="900" y="38" fill="#ff2d95">TOP</text>
    <text x="900" y="62" fill="#f8fafc">{escape(top_language).upper()} {top_percent:.1f}%</text>
    <text x="1034" y="38" fill="#facc15">NEW</text>
    <text x="1034" y="62" fill="#f8fafc">{new_count}</text>
    <text x="1100" y="38" fill="#22d3ee">STARS</text>
    <text x="1100" y="62" fill="#f8fafc">{total_stars}</text>
    <text x="1164" y="38" fill="#ff2d95">FORKS</text>
    <text x="1164" y="62" fill="#f8fafc">{total_forks}</text>
    <text x="1236" y="38" fill="#facc15" text-anchor="end">AUTO</text>
    <text x="1236" y="62" fill="#f8fafc" text-anchor="end">{updated_label}</text>
  </g>
</svg>
"""
    (ASSETS / "signal-strip.svg").write_text(svg, encoding="utf-8", newline="\n")


def render(repos: list[dict[str, Any]], user: dict[str, Any]) -> str:
    public = [repo for repo in repos if not repo.get("private")]
    project_repos = [repo for repo in public if repo["name"] != PROFILE_REPO]
    source_repos = project_repos or public or repos
    stats_repos = [repo for repo in source_repos if not repo.get("fork")] or source_repos
    non_fork_projects = [repo for repo in source_repos if not repo.get("fork")]
    total_stars = sum(repo.get("stargazers_count", 0) for repo in source_repos)
    total_forks = sum(repo.get("forks_count", 0) for repo in source_repos)

    now = dt.datetime.now(dt.UTC)
    updated = now.strftime("%Y-%m-%d %H:%M UTC")
    badge_updated = now.strftime("%Y.%m.%d %H:%M UTC")
    previous_snapshot = load_language_snapshot()
    stats = collect_language_stats(stats_repos, previous_snapshot, updated)
    write_language_snapshot(stats)
    write_hero_svg(stats, updated)
    write_signal_svg(stats, len(non_fork_projects), total_stars, total_forks, updated)

    bio = text(user.get("bio"), "Systems builder focused on data structures, language experiments, and fast tooling.")
    recent = "\n".join(repo_line(repo) for repo in source_repos[:8]) or "- Building in public soon."

    return f"""<!-- AUTO-GENERATED by scripts/build_readme.py. Edit the script, not this file. -->

<p align="center">
  <img width="100%" src="./assets/neon-forge.svg" alt="Tom Lo polyglot systems data scientist banner" />
</p>

<p align="center">
  <img width="100%" src="./assets/signal-strip.svg" alt="Tom Lo language telemetry strip" />
</p>

<p align="center">
  <a href="https://github.com/{USERNAME}?tab=repositories"><img alt="Tracked repos" src="{badge('tracked repos', str(stats.get('repo_count', 0)), '0f172a')}"></a>
  <img alt="Tracked languages" src="{badge('tracked languages', str(len(stats.get('languages', []))), '7c3aed')}">
  <img alt="Language bytes" src="{badge('language bytes', format_bytes(int(stats.get('total_bytes', 0))), '22c55e')}">
  <img alt="Stars" src="{badge('stars', str(total_stars), 'f59e0b')}">
  <img alt="Forks" src="{badge('forks', str(total_forks), '38bdf8')}">
  <img alt="Updated" src="{badge('auto update', badge_updated, '22c55e')}">
</p>

## Language Matrix

**Positioning:** polyglot systems-level data/computer scientist and multidisciplinary programmer. This page tracks the languages actually present in my primary public source projects by repository language bytes, not by a hand-written stack list.

<p align="center">
{language_badges(stats)}
</p>

{new_language_line(stats)}

{language_matrix(stats)}

## Mission Control

{bio}

I work at the intersection of systems programming, data structures, computational thinking, and applied tooling. The goal is to inspect the same ideas through multiple language ecosystems, then compare correctness, ergonomics, and runtime behavior.

```text
identity :: polyglot systems-level data/computer scientist
scope    :: data structures, runtimes, CLI tools, benchmarks
scan     :: daily GitHub language bytes
```

## Project Radar

{project_table(source_repos)}

## Toolchain

<p align="center">
{stack_badges(stats)}
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

This profile README updates itself from GitHub Actions every day. The workflow scans public repository language bytes, detects languages that were not in the previous snapshot, rebuilds this page, and commits the refreshed README plus `assets/language-stats.json`.

<sub>Last generated: {updated}</sub>
"""


def main() -> None:
    user = github_json(f"https://api.github.com/users/{USERNAME}")
    repos = public_repos()
    (ROOT / "README.md").write_text(render(repos, user), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
