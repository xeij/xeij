#!/usr/bin/env python3
"""
Build a neofetch-style GitHub profile README with live stats.

    python build_readme.py            # fetches stats from GitHub, writes dark_mode.svg, light_mode.svg, README.md

Runs inside the GitHub Action in .github/workflows/update-readme.yml, which
provides GH_TOKEN. Locally: export GH_TOKEN=<a personal token> first.
No dependencies beyond the standard library.
"""
import json
import os
import sys
import time
import urllib.request
from datetime import date

USER = "xeij"
BORN = date(2002, 4, 8)

INFO_WIDTH = 64

TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")


# ----------------------------------------------------------------- GitHub API
def graphql(query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql", data=body,
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.load(r)
    if "errors" in data:
        raise SystemExit(data["errors"])
    return data["data"]


def rest(path):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={"Authorization": f"bearer {TOKEN}", "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status, json.load(r)


def fetch_stats():
    if not TOKEN:
        print("no GH_TOKEN, using placeholder stats", file=sys.stderr)
        return dict(repos="?", contributed="?", stars="?", commits="?",
                    followers="?", loc="?", adds="?", dels="?")

    q = """
    query($login:String!) {
      user(login:$login) {
        followers { totalCount }
        repositories(first:100, ownerAffiliations:OWNER, isFork:false) {
          totalCount
          nodes { name stargazerCount }
        }
        repositoriesContributedTo(first:1, contributionTypes:[COMMIT, PULL_REQUEST, ISSUE, REPOSITORY]) {
          totalCount
        }
        contributionsCollection { contributionYears }
      }
    }"""
    u = graphql(q, {"login": USER})["user"]
    repos = u["repositories"]["nodes"]
    stars = sum(r["stargazerCount"] for r in repos)

    # total commits = commit contributions summed over every year on GitHub
    commits = 0
    for y in u["contributionsCollection"]["contributionYears"]:
        c = graphql("""
        query($login:String!, $from:DateTime!, $to:DateTime!) {
          user(login:$login) {
            contributionsCollection(from:$from, to:$to) {
              totalCommitContributions restrictedContributionsCount
            }
          }
        }""", {"login": USER, "from": f"{y}-01-01T00:00:00Z", "to": f"{y}-12-31T23:59:59Z"})
        cc = c["user"]["contributionsCollection"]
        commits += cc["totalCommitContributions"] + cc["restrictedContributionsCount"]

    # lines of code: this user's additions/deletions across owned repos
    adds = dels = 0
    for r in repos:
        stats = None
        for attempt in range(6):                    # GitHub computes stats lazily
            try:                                     # and answers 202 until ready
                status, stats = rest(f"/repos/{USER}/{r['name']}/stats/contributors")
            except Exception as e:                   # empty repo, etc.
                print(f"skip {r['name']}: {e}", file=sys.stderr)
                stats = None
                break
            if status == 200 and isinstance(stats, list):
                break
            time.sleep(3)
        if not isinstance(stats, list):
            print(f"stats not ready for {r['name']}", file=sys.stderr)
            continue
        for c in stats:
            if (c.get("author") or {}).get("login", "").lower() == USER.lower():
                for w in c["weeks"]:
                    adds += w["a"]; dels += w["d"]

    return dict(
        repos=u["repositories"]["totalCount"],
        contributed=u["repositoriesContributedTo"]["totalCount"],
        stars=stars, commits=commits,
        followers=u["followers"]["totalCount"],
        loc=adds - dels, adds=adds, dels=dels,
    )


# ---------------------------------------------------------------- info column
def uptime(born=BORN):
    from calendar import monthrange
    t = date.today()
    years = t.year - born.year - ((t.month, t.day) < (born.month, born.day))
    months = (t.month - born.month - (t.day < born.day)) % 12
    if t.day >= born.day:
        days = t.day - born.day
    else:
        pm, py = (t.month - 1 or 12), (t.year if t.month > 1 else t.year - 1)
        days = monthrange(py, pm)[1] - born.day + t.day
    p = lambda n, w: f"{n} {w}" + ("" if n == 1 else "s")
    return f"{p(years,'year')}, {p(months,'month')}, {p(days,'day')}"


def fmt(n):
    return f"{n:,}" if isinstance(n, int) else str(n)


def build_info(s):
    return [
        "shaya@xeij",
        ("OS", "macOS 26, Arch Linux"),
        ("Uptime", uptime()),
        ("Host", "MacBook Air M5 (2026)"),
        ("Host.Legacy", "ThinkPad, Arch Linux + i3"),
        ("Kernel", "M.Sc. AI, UPC Barcelona"),
        ("Shell", "zsh + Starship"),
        ("Editor", "Neovim"),
        "",
        ("Languages.Programming", "Python, C++, Rust, TypeScript, SQL"),
        ("Languages.ML", "PyTorch, scikit-learn, XGBoost, LangGraph"),
        ("Languages.Cloud", "AWS, Docker, Kubernetes, Terraform"),
        ("Languages.Data", "PostgreSQL, Redis, Kafka"),
        ("Languages.Real", "English, Persian, Spanish"),
        ("Hobbies.Software", "Minecraft Modding, Game AI"),
        ("Hobbies.Markets", "Options, Quant Finance"),
        "",
        "Focus",
        ("Research", "ML Models, Multi Agent Systems, Computer Vision"),
        ("Founder", "Stateira Labs, 1,500+ MAU trading terminal"),
        ("Previously", "TA, WSU EECS, 300+ students"),
        "",
        "Contact",
        ("Web", "xeijs.com"),
        ("GitHub", "github.com/xeij"),
        ("LinkedIn", "linkedin.com/in/xeij"),
        ("Email", "xeijs@yahoo.com"),
        "",
        "GitHub Stats",
        ("Repos", f"{fmt(s['repos'])} {{Contributed: {fmt(s['contributed'])}}} | Stars: {fmt(s['stars'])}"),
        ("Commits", f"{fmt(s['commits'])} | Followers: {fmt(s['followers'])}"),
        ("Lines of Code", f"{fmt(s['loc'])} ( {fmt(s['adds'])}++, {fmt(s['dels'])}-- )"),
    ]




# ------------------------------------------------------------------- portrait
ART = r"""
                               +:-*.
                      :+-- .###++*=#%+*%%=-
                 .. =#=-:+%#%%%%%%%%%%%%%%%%%%*:  .
                 . -*=###%%%%%%%%%%%%%%%%%%%%%%#-:-*:
               .+=+##%##%%%%%%%%%%%%%%%%%%%%%%%%%*#%%*.
             ..=#####%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%.
          .   :#%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%###:
         :=.--#%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%+##.
         .#=##%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%-
          -#%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%#:
          :#%%%%%%%%%%%%%%%%%%%##%%%%%%%%%%%%%%%%%%%%%%%%%%%=
         :+#%%%%%%%%%%%%%%%%%%%##**##+##%%%%%%%%%%%%%%%%%%%%*
        -+#%%%%%%%%%%%%%%%%%%#%%#-=-=*%%#%%%%%%%%%%%%%%%%%%%#
        :+#%%%%%%%%%%%%%%%%#%%%%=--:-+%%###%%%%%%%%%%%%%%%%%#*
        -##%%%%%%%%%%%%#%%%%%%%#-:::::-=**#*+#%%%%%%%%%%%%%%%+
        +%%%%%%%%%%%###%%%%%%%%+:::..::-==+*#%%%%%%%%%%%%%%%%=
        .*%%%%%%%%%#%%%%%%%%%%%%*-::::=*#%%%%#%%##%%%%%%%%%%*=
         +#%%%%%%%%##****##%%%##*=-:::-+**+++***+*#%%%%%%%%%#.
        .=#%%%%%%%%#***#####***##*-::-=***#%####**#*%%%%%%%%*
       ::##%%%%%%#%+++*##=#%%:-***=---=+++++*+*+===+*%%%%%%%:
        *+=%%%%%%##+====+*++++=+++=:::-===-==-------=+#%%#%#-
         ..=##%%%#+===--=-----===---::-------::::----=*%%%%#
           :++#%%#+=-----------===--::--::::::::::::-=*%%#=.
           +=++#%%=------------=+-::.:::-:::::::::::-=%+-=.
            .-=+*#+==----------==++=--++:-:::::::::--==:::
             :==-+#==-----------+*=++=-=-::::::::---=*=.:
              -=-=*++==--------==+++++++=---:::::--=+*=:
               -#%%+++==---===+##%##+*##%%#+=----===++
               .#*#**+++===+###++**+==+*++*##*=-====+.
                -#%%++*++=+#**#+====---===++*#==++++*
                 :=%#**+++*+====++========--=+++*+**:
                   ##****+**+==++*###%##+====++*###-
                    -=+##****+===-----:-==+*+*#*#%=
                     ==*#%##++===--==-=====+*##%*==
                     ==++*%%#****##*+***#*###%#+===
                     -=+++**%%%%%%%##%%%%%%%#+=====
                     ====++++*%%%%%%%%%%%#++===-==+%@@%%
                =%%%%*+=====++++++++++======-----==%@@@%%=
              %%%%%%%*+======++++===--------------=+%@%%%%%
             %%%%%%%%*+========++==-----------::---=#%%%%%%%*
            *%%%%%%%#*+====-=========-------:::::--=%%%%%%%%%%#:
           +%%%%%%%%#*+===-----=====----::::::::::=*%%%%%%%%%%%%%%%%%%
       *%%%%%%%%%%%%%#+====-----------:::::::::::-*%%%%%%%%%%%%%%%%%%.
  +%%%%%%%%%%%%%%%%%%%*====----------::::::::::-=+%%%%%%%%%%%%%%%%%%%.
%%%%%%%%%%%%%%%%%%%%%%%*====----------:::::::--=+%%%%%%%%%%%%%%%%%%%%:
""".splitlines()

# ---------------------------------------------------------------------- SVG
from xml.sax.saxutils import escape

FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"
FS = 12.5          # font size px
CW = FS * 0.602    # monospace advance width
LH = 16            # line height px
PAD = 28
GAP_PX = 36

THEMES = {
    "dark":  dict(bg="#0d1117", art="#f0883e", key="#58a6ff", val="#e6edf3",
                  head="#f0883e", rule="#30363d", add="#3fb950", rm="#f85149", dots="#6e7681"),
    "light": dict(bg="#ffffff", art="#bc4c00", key="#0969da", val="#1f2328",
                  head="#bc4c00", rule="#d0d7de", add="#1a7f37", rm="#cf222e", dots="#8c959f"),
}


def tspan(text, color, bold=False):
    w = ' font-weight="600"' if bold else ""
    return f'<tspan fill="{color}"{w}>{escape(text)}</tspan>'


def info_line_svg(item, c, first):
    """Return a list of tspans for one info entry."""
    if isinstance(item, str):
        if not item:
            return []
        head = f"- {item} " if not first else f"{item} "
        return [tspan(head, c["head"], True), tspan("─" * (INFO_WIDTH - len(head)), c["rule"])]
    k, v = item
    key = f"- {k}: "
    dots = INFO_WIDTH - len(key) - len(v) - 1
    if dots < 1:
        raise SystemExit(f"'{k}' too long for INFO_WIDTH, shorten or raise it")
    parts = [tspan(key, c["key"]), tspan("." * dots + " ", c["dots"])]
    if k == "Lines of Code":           # colour the ++ / -- like a diff
        base, rest = v.split(" ( ", 1)
        adds, dels = rest.rstrip(" )").split(", ")
        parts += [tspan(base + " ( ", c["val"]), tspan(adds, c["add"]),
                  tspan(", ", c["val"]), tspan(dels, c["rm"]), tspan(" )", c["val"])]
    else:
        parts.append(tspan(v, c["val"]))
    return parts


def render_svg(info, theme):
    c = THEMES[theme]
    art_w = max(len(l) for l in ART)
    n = max(len(ART), len(info))
    pad = (n - len(info)) // 2                  # centre the shorter column
    info = [""] * pad + info + [""] * (n - pad - len(info))
    art = ART + [""] * (n - len(ART))

    x_art = PAD
    x_info = PAD + art_w * CW + GAP_PX
    width = x_info + INFO_WIDTH * CW + PAD
    height = PAD * 2 + n * LH

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height}" '
           f'viewBox="0 0 {width:.0f} {height}" font-family="{FONT}" font-size="{FS}">',
           f'<rect width="100%" height="100%" rx="6" fill="{c["bg"]}"/>']
    first = True
    for i, (a, b) in enumerate(zip(art, info)):
        y = PAD + (i + 1) * LH - 4
        if a:
            out.append(f'<text x="{x_art}" y="{y}" xml:space="preserve">{tspan(a, c["art"])}</text>')
        parts = info_line_svg(b, c, first)
        if parts:
            first = False
            out.append(f'<text x="{x_info:.1f}" y="{y}" xml:space="preserve">{"".join(parts)}</text>')
    out.append("</svg>")
    return "\n".join(out)


def main():
    info = build_info(fetch_stats())
    for theme in THEMES:
        with open(f"{theme}_mode.svg", "w", encoding="utf-8") as f:
            f.write(render_svg(info, theme))
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(
            '<picture>\n'
            '  <source media="(prefers-color-scheme: dark)" srcset="dark_mode.svg">\n'
            '  <source media="(prefers-color-scheme: light)" srcset="light_mode.svg">\n'
            '  <img alt="xeij profile" src="dark_mode.svg">\n'
            '</picture>\n'
        )
    print("wrote dark_mode.svg, light_mode.svg, README.md")


if __name__ == "__main__":
    main()
