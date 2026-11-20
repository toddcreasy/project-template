"""One daily email with GitHub traffic for every repo in REPOS, as an HTML table.

GitHub keeps repo traffic for 14 days only, so each run also saves a raw snapshot per repo and
folds the daily counts into a per-repo history in S3. A repo the token can't read shows its error
in the email instead of stopping the others.
"""

import datetime
import html
import ipaddress
import json
import os
import time
import urllib.request

import boto3

REPOS = json.loads(os.environ["REPOS"])
BUCKET = os.environ["BUCKET"]
EMAIL = os.environ["EMAIL"]
# App log groups whose page views carry the visitor's address (a "client" field); and the
# maintainer's own addresses, left out of the visitor table.
LOG_GROUPS = json.loads(os.environ.get("LOG_GROUPS", "[]"))
MY_IPS = set(json.loads(os.environ.get("MY_IPS", "[]")))
BOTS = ("bot", "crawl", "spider", "slurp", "curl", "python", "go-http", "headless", "scan", "wget")
MAX_VISITORS = 40

s3 = boto3.client("s3")


def fetch(repo: str, path: str, token: str):
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/traffic/{path}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "repo-traffic",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def snapshot_of(repo: str, token: str) -> dict:
    return {
        "views": fetch(repo, "views", token),
        "clones": fetch(repo, "clones", token),
        "referrers": fetch(repo, "popular/referrers", token),
        "paths": fetch(repo, "popular/paths", token),
    }


def key(repo: str) -> str:
    return repo.replace("/", "__")


def update_history(repo: str, snapshot: dict) -> dict:
    """Each run rewrites the days GitHub still returns, so today's partial count is corrected
    tomorrow and older days keep their final value."""
    path = f"history/{key(repo)}.json"
    try:
        history = json.load(s3.get_object(Bucket=BUCKET, Key=path)["Body"])
    except s3.exceptions.NoSuchKey:
        history = {"views": {}, "clones": {}}
    for kind in ("views", "clones"):
        for day in snapshot[kind][kind]:
            history[kind][day["timestamp"][:10]] = {"count": day["count"], "uniques": day["uniques"]}
    s3.put_object(Bucket=BUCKET, Key=path, Body=json.dumps(history, sort_keys=True))
    return history


def summary(repo: str, snapshot: dict, history: dict, yesterday: str) -> dict:
    views = snapshot["views"]
    day = next((d for d in views["views"] if d["timestamp"].startswith(yesterday)), None)
    return {
        # Display name only: every repo is the same owner.
        "repo": repo.split("/")[-1],
        "yesterday_views": day["count"] if day else 0,
        "yesterday_unique": day["uniques"] if day else 0,
        "views_14d": views["count"],
        "unique_14d": views["uniques"],
        "views_all": sum(d["count"] for d in history["views"].values()),
        "since": min(history["views"], default=yesterday),
        "referrers": snapshot["referrers"],
        # Paths read /owner/repo/...; the Repo column already names the repo.
        "paths": [
            {**p, "path": p["path"].removeprefix(f"/{repo}") or "/"} for p in snapshot["paths"]
        ],
    }


def page_views(log_group: str, day: datetime.date) -> list[dict]:
    """One UTC day's page views with a visitor address, through CloudWatch Logs Insights."""
    logs = boto3.client("logs")
    start = datetime.datetime.combine(day, datetime.time(), datetime.UTC)
    try:
        query_id = logs.start_query(
            logGroupName=log_group,
            startTime=int(start.timestamp()),
            endTime=int((start + datetime.timedelta(days=1)).timestamp()) - 1,
            queryString="fields @timestamp, client, user_agent, path"
            " | filter ispresent(client) | sort @timestamp asc | limit 10000",
        )["queryId"]
    except logs.exceptions.MalformedQueryException as exc:
        # Logs Insights refuses a window that ends before the log group was created (a
        # redeploy can recreate it): nothing could have been logged that day.
        if "creation time" in str(exc):
            return []
        raise
    for _ in range(60):
        result = logs.get_query_results(queryId=query_id)
        if result["status"] not in ("Scheduled", "Running"):
            break
        time.sleep(1)
    return [{f["field"]: f["value"] for f in row} for row in result["results"]]


def owner(address: str) -> tuple[str, str]:
    """(organization, country) from RDAP, the regional registries' public lookup. Only the
    registrant organization: RDAP also lists contacts, who are people, and those are skipped."""
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return "", ""
    request = urllib.request.Request(
        f"https://rdap.org/ip/{ip}", headers={"Accept": "application/rdap+json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            data = json.load(response)
    except Exception:
        return "", ""
    for entity in data.get("entities", []):
        if "registrant" not in entity.get("roles", []):
            continue
        card = {f[0]: f[3] for f in entity.get("vcardArray", [None, []])[1]}
        if card.get("kind") == "org" and card.get("fn"):
            return card["fn"], data.get("country", "")
    return data.get("name", ""), data.get("country", "")


def browser(agent: str) -> str:
    for name in ("Edg", "Chrome", "Firefox", "Safari"):
        if name in agent:
            kind = "Edge" if name == "Edg" else name
            break
    else:
        kind = "Other"
    device = "phone" if "Mobile" in agent else "desktop"
    return f"{kind}, {device}"


def demo_visitors(day: datetime.date) -> tuple[list[list], str | None]:
    """Rows for the visitor table, and an error if a log group couldn't be read."""
    visitors: dict[tuple[str, str], dict] = {}
    for group in LOG_GROUPS:
        try:
            views = page_views(group, day)
        except Exception as exc:
            return [], f"{group}: {str(exc)[:200]}"
        site = group.rsplit("/", 1)[-1]
        for v in views:
            agent = v.get("user_agent", "")
            if v["client"] in MY_IPS or any(b in agent.lower() for b in BOTS):
                continue
            entry = visitors.setdefault(
                (site, v["client"]), {"first": v["@timestamp"][11:16], "pages": [], "agent": agent}
            )
            entry["pages"].append(v["path"])
    rows = []
    for (site, address), v in list(visitors.items())[:MAX_VISITORS]:
        org, country = owner(address)
        pages = ", ".join(dict.fromkeys(v["pages"]))
        rows.append([site, v["first"], org or "(unknown)", country, len(v["pages"]), pages,
                     browser(v["agent"])])
    return rows, None


CELL = "padding:4px 8px;border-bottom:1px solid #d4e0e8;text-align:{align}"
HEAD = "padding:4px 8px;border-bottom:2px solid #1c2e4a;text-align:{align};color:#1c2e4a"


def table(headers: list[str], rows: list[list], numeric_from: int = 1) -> str:
    def align(i: int) -> str:
        return "right" if i >= numeric_from else "left"

    head = "".join(
        f'<th style="{HEAD.format(align=align(i))}">{html.escape(h)}</th>'
        for i, h in enumerate(headers)
    )
    body = "".join(
        "<tr>"
        + "".join(
            f'<td style="{CELL.format(align=align(i))}">{html.escape(str(v))}</td>'
            for i, v in enumerate(row)
        )
        + "</tr>"
        for row in rows
    )
    return (
        '<table style="border-collapse:collapse;margin:6px 0 16px;font-size:12px">'
        f"{head}{body}</table>"
    )


def render(
    summaries: list[dict], errors: dict, yesterday: str, visitors: list[list], visitor_error
) -> tuple[str, str]:
    headers = [
        "Repo",
        f"Views {yesterday}",
        "Unique",
        "Views 14 days",
        "Unique",
        "Views since tracking began",
    ]
    rows = [
        [
            s["repo"],
            s["yesterday_views"],
            s["yesterday_unique"],
            s["views_14d"],
            s["unique_14d"],
            f"{s['views_all']} (since {s['since']})",
        ]
        for s in summaries
    ]
    referrers = [
        [s["repo"], r["referrer"], r["count"], r["uniques"]] for s in summaries for r in s["referrers"]
    ]
    pages = [[s["repo"], p["path"], p["count"], p["uniques"]] for s in summaries for p in s["paths"]]
    parts = [
        '<div style="font-family:-apple-system,Helvetica,Arial,sans-serif;color:#1c2e4a;'
        'font-size:13px">',
        f"<h2 style=\"margin:0 0 6px;font-size:16px\">Repo traffic, {yesterday}</h2>",
        table(headers, rows),
        "<h3 style=\"margin:0;font-size:14px\">Referrers, last 14 days</h3>",
        table(["Repo", "Referrer", "Views", "Unique"], referrers, numeric_from=2)
        if referrers
        else "<p>None.</p>",
        "<h3 style=\"margin:0;font-size:14px\">Pages, last 14 days</h3>",
        table(["Repo", "Page", "Views", "Unique"], pages, numeric_from=2) if pages else "<p>None.</p>",
    ]
    if LOG_GROUPS:
        parts.append(
            f"<h3 style=\"margin:0;font-size:14px\">Demo site visitors, {yesterday} (UTC)</h3>"
        )
        if visitor_error:
            parts.append(f"<p>Not read: {html.escape(visitor_error)}</p>")
        elif visitors:
            parts.append(
                table(
                    ["Site", "First (UTC)", "Network owner", "Country", "Views", "Pages", "Browser"],
                    visitors,
                    numeric_from=4,
                )
            )
        else:
            parts.append("<p>None.</p>")
    if errors:
        parts.append("<h3 style=\"margin:0;font-size:14px\">Not fetched</h3>")
        parts.append(table(["Repo", "Error"], [[r, e] for r, e in errors.items()], numeric_from=9))
    parts.append(
        '<p style="color:#4a5b73;font-size:12px">GitHub keeps 14 days; the history in S3 keeps'
        " the rest. Clones are left out: GitHub doesn't say who cloned, and most clones come from"
        " CI and crawlers; the snapshots in S3 still have them. Demo site visitors leave out"
        " bots and your own addresses; the network owner is the organization registered for"
        " the address (a company, a university, or a home ISP), never a person.</p></div>"
    )
    text = [f"Repo traffic, {yesterday}", ""]
    for s in summaries:
        text.append(
            f"{s['repo']}: yesterday {s['yesterday_views']} views ({s['yesterday_unique']} unique);"
            f" 14 days {s['views_14d']} views ({s['unique_14d']} unique)"
        )
    text += [f"{r}: not fetched ({e})" for r, e in errors.items()]
    if LOG_GROUPS:
        text.append(f"Demo site visitors: {len(visitors)}")
        text += [f"  {v[0]} {v[1]} {v[2]} [{v[3]}] {v[4]} views: {v[5]}" for v in visitors]
    return "".join(parts), "\n".join(text)


def handler(event, context):
    secrets = boto3.client("secretsmanager")
    token = secrets.get_secret_value(SecretId=os.environ["TOKEN_SECRET_ARN"])["SecretString"]
    today = datetime.datetime.now(datetime.UTC).date()
    yesterday = str(today - datetime.timedelta(days=1))
    summaries, errors = [], {}
    for repo in REPOS:
        try:
            snapshot = snapshot_of(repo, token)
        except Exception as exc:  # one repo's failure must not stop the email
            errors[repo.split("/")[-1]] = str(exc)[:200]
            continue
        s3.put_object(
            Bucket=BUCKET, Key=f"snapshots/{key(repo)}/{today}.json", Body=json.dumps(snapshot)
        )
        summaries.append(summary(repo, snapshot, update_history(repo, snapshot), yesterday))
    visitors, visitor_error = demo_visitors(today - datetime.timedelta(days=1))
    body_html, body_text = render(summaries, errors, yesterday, visitors, visitor_error)
    boto3.client("sesv2").send_email(
        FromEmailAddress=EMAIL,
        Destination={"ToAddresses": [EMAIL]},
        Content={
            "Simple": {
                "Subject": {"Data": f"Repo traffic, {yesterday}"},
                "Body": {"Html": {"Data": body_html}, "Text": {"Data": body_text}},
            }
        },
    )
    if errors and not summaries:
        # Nothing fetched (an expired token, usually): fail the run so the alarm fires.
        raise RuntimeError(f"no repo fetched: {errors}")
    return {"repos": len(summaries), "errors": errors}
