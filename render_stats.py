#!/usr/bin/env python3
"""Render GitHub profile stat cards as SVGs — no external stat services.

Outputs:
  assets/stats-card.svg    — totals card (repos, stars, forks, followers, contributions)
  assets/top-langs.svg     — language usage stacked bar + legend
"""
import base64, json, os, urllib.request
from collections import defaultdict

USER = "Johnie-Musyoki"
TOKEN = os.environ["GH_TOKEN"]
OUT = "assets"
os.makedirs(OUT, exist_ok=True)

GREEN = "#00E676"
TXT = "#c9d1d9"
MUTED = "#8b949e"
BG = "#0d1117"
BORDER = "#21262d"

def gh(url):
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "profile-stats",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

# ---- collect data ----
profile = gh(f"https://api.github.com/users/{USER}")
followers = profile["followers"]

stars = forks = 0
langs_bytes = defaultdict(int)
repo_count = 0
page = 1
while True:
    repos = gh(f"https://api.github.com/users/{USER}/repos?per_page=100&fork=false&page={page}")
    if not repos:
        break
    for r in repos:
        repo_count += 1
        stars += r["stargazers_count"]
        forks += r["forks_count"]
        if r.get("language"):
            # weight by repo size (KB) as a proxy for language share
            langs_bytes[r["language"]] += max(r.get("size", 1), 1)
    page += 1

# contributions last year via GraphQL (graceful fallback)
contributions = None
try:
    gql = json.dumps({"query":
        '{ viewer { login } }'}).encode()  # placeholder replaced below
    q = {"query": f'''query {{ user(login: "{USER}") {{
        contributionsCollection {{ contributionCalendar {{ totalContributions }} }}
    }} }}'''}
    req = urllib.request.Request("https://api.github.com/graphql",
        data=json.dumps(q).encode(),
        headers={"Authorization": f"Bearer {TOKEN}", "User-Agent": "profile-stats"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    contributions = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]
except Exception:
    pass

def fmt(n):
    return f"{n:,}"

# ---- stats card ----
rows = [
    ("📦", "Total Repositories", fmt(repo_count)),
    ("⭐", "Total Stars Earned", fmt(stars)),
    ("🍴", "Total Forks", fmt(forks)),
    ("👥", "Followers", fmt(followers)),
]
if contributions is not None:
    rows.append(("🔥", "Contributions (last year)", fmt(contributions)))

W, H = 460, 70 + len(rows) * 34
parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
    f'<rect width="{W}" height="{H}" rx="12" fill="{BG}" stroke="{BORDER}"/>',
    f'<text x="24" y="40" font-family="Segoe UI,Helvetica,Arial" font-size="18" font-weight="700" fill="{TXT}">John\'s GitHub</text>',
    f'<text x="{W-24}" y="40" text-anchor="end" font-family="Segoe UI" font-size="13" fill="{MUTED}">🇰🇪 · Security Engineer</text>',
]
y = 78
for icon, label, val in rows:
    parts.append(f'<text x="28" y="{y}" font-size="15">{icon}</text>')
    parts.append(f'<text x="58" y="{y}" font-family="Segoe UI" font-size="14" fill="{MUTED}">{label}</text>')
    parts.append(f'<text x="{W-28}" y="{y}" text-anchor="end" font-family="Consolas,monospace" font-size="15" font-weight="700" fill="{GREEN}">{val}</text>')
    y += 34
parts.append("</svg>")
open(f"{OUT}/stats-card.svg", "w").write("\n".join(parts))

# ---- languages card ----
total = sum(langs_bytes.values())
top = sorted(langs_bytes.items(), key=lambda kv: -kv[1])[:8]
palette = ["#3178C6","#F7DF1E","#3776AB","#00ADD8","#E34C26","#777BB4","#DEA584","#0175C2",
           "#A97BFF","#563D7C","#89e051","#384d54","#b07219","#6699CC","#000080","#f1e05a"]
lang_colors = {
    "TypeScript":"#3178C6","JavaScript":"#F1E05A","Python":"#3572A5","Go":"#00ADD8",
    "PHP":"#4F5D95","Dart":"#00B4AB","HTML":"#E34C26","CSS":"#563D7C","Shell":"#89E051",
    "Jupyter Notebook":"#DA5B0B","Java":"#B07219","C++":"#F34B7D","C":"#555555","Ruby":"#701516",
}
CW, CH = 460, 60 + len(top) * 30 + 30
p = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{CW}" height="{CH}" viewBox="0 0 {CW} {CH}">',
    f'<rect width="{CW}" height="{CH}" rx="12" fill="{BG}" stroke="{BORDER}"/>',
    f'<text x="24" y="36" font-family="Segoe UI,Helvetica,Arial" font-size="16" font-weight="700" fill="{TXT}">Most Used Languages</text>',
]
# stacked bar
bx, bw, by, bh = 24, CW - 48, 52, 10
x = bx
for i, (name, sz) in enumerate(top):
    w = bw * sz / total
    c = lang_colors.get(name, palette[i % len(palette)])
    p.append(f'<rect x="{x:.1f}" y="{by}" width="{w+0.5:.1f}" height="{bh}" fill="{c}" rx="2"/>')
    x += w
# legend
ly = 92
for i, (name, sz) in enumerate(top):
    c = lang_colors.get(name, palette[i % len(palette)])
    col = i % 2
    lx = 24 + col * 210
    p.append(f'<circle cx="{lx+5}" cy="{ly-5}" r="5" fill="{c}"/>')
    p.append(f'<text x="{lx+18}" y="{ly}" font-family="Segoe UI" font-size="12.5" fill="{TXT}">{name}</text>')
    p.append(f'<text x="{lx+196}" y="{ly}" text-anchor="end" font-family="Segoe UI" font-size="11.5" fill="{MUTED}">{sz*100//max(total,1)}%</text>')
    if col == 1:
        ly += 30
p.append("</svg>")
open(f"{OUT}/top-langs.svg", "w").write("\n".join(p))

print(f"stats-card: repos={repo_count} stars={stars} forks={forks} followers={followers} contribs={contributions}")
print(f"top-langs: {[k for k,_ in top]}")
