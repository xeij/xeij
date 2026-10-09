#!/usr/bin/env python3
import json
import os
import sys
import urllib.request
from datetime import date

USER = "xeij"
BORN = date(2002, 4, 8)

ART_WIDTH = 40
ART_HEIGHT = 34
INFO_WIDTH = 64
GAP = "   "

TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")


# ----------------------------------------------------------------- GitHub API
def graphql(query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={
            "Authorization": f"bearer {TOKEN}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.load(r)
    if "errors" in data:
        raise SystemExit(data["errors"])
    return data["data"]


def rest(path):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "Authorization": f"bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status, json.load(r)


def fetch_stats():
    if not TOKEN:
        print("no GH_TOKEN, using placeholder stats", file=sys.stderr)
        return dict(
            repos="?",
            contributed="?",
            stars="?",
            commits="?",
            followers="?",
            loc="?",
            adds="?",
            dels="?",
        )

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
        c = graphql(
            """
        query($login:String!, $from:DateTime!, $to:DateTime!) {
          user(login:$login) {
            contributionsCollection(from:$from, to:$to) {
              totalCommitContributions restrictedContributionsCount
            }
          }
        }""",
            {
                "login": USER,
                "from": f"{y}-01-01T00:00:00Z",
                "to": f"{y}-12-31T23:59:59Z",
            },
        )
        cc = c["user"]["contributionsCollection"]
        commits += cc["totalCommitContributions"] + cc["restrictedContributionsCount"]

    # lines of code: this user's additions/deletions across owned repos
    adds = dels = 0
    for r in repos:
        try:
            status, stats = rest(f"/repos/{USER}/{r['name']}/stats/contributors")
        except Exception as e:  # empty repo, etc.
            print(f"skip {r['name']}: {e}", file=sys.stderr)
            continue
        if status == 202 or not isinstance(stats, list):  # GitHub still computing
            continue
        for c in stats:
            if (c.get("author") or {}).get("login", "").lower() == USER.lower():
                for w in c["weeks"]:
                    adds += w["a"]
                    dels += w["d"]

    return dict(
        repos=u["repositories"]["totalCount"],
        contributed=u["repositoriesContributedTo"]["totalCount"],
        stars=stars,
        commits=commits,
        followers=u["followers"]["totalCount"],
        loc=adds - dels,
        adds=adds,
        dels=dels,
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
    return f"{p(years, 'year')}, {p(months, 'month')}, {p(days, 'day')}"


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
        (
            "Repos",
            f"{fmt(s['repos'])} {{Contributed: {fmt(s['contributed'])}}} | Stars: {fmt(s['stars'])}",
        ),
        ("Commits", f"{fmt(s['commits'])} | Followers: {fmt(s['followers'])}"),
        (
            "Lines of Code",
            f"{fmt(s['loc'])} ( {fmt(s['adds'])}++, {fmt(s['dels'])}-- )",
        ),
    ]


def render_info(info):
    out = []
    for item in info:
        if isinstance(item, str):
            if item == "":
                out.append("")
            else:
                head = f"- {item} " if out else f"{item} "
                out.append(head + "─" * (INFO_WIDTH - len(head)))
        else:
            k, v = item
            key = f"- {k}: "
            dots = INFO_WIDTH - len(key) - len(v) - 1
            if dots < 1:
                raise SystemExit(f"'{k}' too long for INFO_WIDTH, shorten or raise it")
            out.append(f"{key}{'.' * dots} {v}")
    return out


# ------------------------------------------------------------------- portrait
ART = r"""
                 :?  .
            ])(JbLQpdhc<
           )UUqWWW&8W#&8p;_
         ;zbhh#WMM&8WWM&%hdc`
         u*ho#W#MWMW&&#W%%&&or
        [aM##MM##M#W&&#*&&#Wkq`
      .zbMWMWW###WW&WMM##WWM#Wf
       0WMWWMWWW#oMWW***#M&WWWw
       m#*WMMWWMoqOwpaoo*MW&W#*
      (a*M#W&W#o*Q_/kha*MW#MWM*:
      x*#WWWM*aa#t';rLZq#8W*WWW\
      Z*#MM*koo#o<  .1nQ**##WM8\
      nW&&#khooWMz^ _QpZppo####_
      {*WMoqQOqbmL< ]YYXXUq#W&W,
      n*WWazcm0qjU(^1nnQxnjq8%b
      tbW&d\{tx/{f?'>?__<i<\h#m
       ]wWL]<<<<_[~`::"^'`"+dW/
       ;xbJ+>IIl<[; '"`'. `+L)
        ?/c?<l:"l}|<]!^'.^:]_
         _r(+>;,;}r/1<`'',>x-
         {Zn{~i+(zCxCY(>:i{f
         >hJf{{LqCU\fcmL?}/>
          Xpcjrznt]--]{x\fc'
           CCUn|{tcXv(+{nQx
           `rwLu|]]1_?/uQpl
            ?CaQ/(]?}|nZpj
            >fChdbbZdhadf}`
            [(/cq*MM*bX1__LWX
         ]w%c}{(tjtt(]+>i>z$$z
        ($@8v}]}()_i<<iI;I}*&%Y
        a&&hx{__}){_>l;"`^]oWM%Y:
       X%&&*u}_i<?]+I"'..`n&WMWWW*ql
   ,rw&%&&&%Z}?>I!i;". .`+kWMW&M#MB!
  L8%%88888&Wj]+lIlI:. ^iz&WMW&MMM8!
""".splitlines()


def main():
    info = render_info(build_info(fetch_stats()))
    art = list(ART)
    n = max(len(art), len(info))
    pad = (n - len(art)) // 2
    art = [""] * pad + art + [""] * (n - pad - len(art))
    info += [""] * (n - len(info))
    block = "\n".join(
        (a.ljust(ART_WIDTH) + GAP + b).rstrip() for a, b in zip(art, info)
    )

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(f'<div align="center">\n\n```text\n{block}\n```\n\n</div>\n')
    print(f"wrote README.md ({n} lines)")


if __name__ == "__main__":
    main()
