#!/usr/bin/env python3
"""
af — job application toolkit.

One profile, many fast outputs. No dependencies beyond the standard library
on Python 3.11+ (uses tomllib). On 3.9/3.10, `pip install tomli`.

    ./af sheet                      cheat sheet for filling a form
    ./af get email --copy           one value, onto your clipboard
    ./af answer "why this company"  reusable answer for a free-text box
    ./af export                     flat JSON for autofill extensions
    ./af resume --tags backend      generate a tailored resume variant
    ./af log add ...                track an application
    ./af doctor                     what's still blank
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ModuleNotFoundError:
        sys.exit(
            "af needs TOML support.\n"
            "  Python 3.11+ has it built in — you're on "
            f"{sys.version_info.major}.{sys.version_info.minor}.\n"
            "  Fix: pip install tomli"
        )

ROOT = Path(__file__).resolve().parent.parent
PROFILE = ROOT / "profile" / "profile.toml"
ANSWERS = ROOT / "profile" / "answers.toml"
RESUME_BASE = ROOT / "resume" / "base.toml"
LOG_CSV = ROOT / "applications" / "log.csv"

# ---------------------------------------------------------------------------
# terminal helpers
# ---------------------------------------------------------------------------

_USE_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def _c(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _USE_COLOR else text


def bold(t: str) -> str:
    return _c(t, "1")


def dim(t: str) -> str:
    return _c(t, "2")


def cyan(t: str) -> str:
    return _c(t, "36")


def yellow(t: str) -> str:
    return _c(t, "33")


def red(t: str) -> str:
    return _c(t, "31")


def green(t: str) -> str:
    return _c(t, "32")


def load(path: Path) -> dict:
    if not path.exists():
        example = path.with_name(path.name.replace(".toml", ".example.toml"))
        hint = "\n  run: ./af init" if example.exists() else ""
        sys.exit(f"missing file: {path.relative_to(ROOT)}{hint}")
    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        sys.exit(f"{path.relative_to(ROOT)} is not valid TOML:\n  {exc}")


def flatten(obj, prefix: str = "") -> dict[str, object]:
    """Flatten nested dicts/lists into dotted paths: personal.address.city."""
    out: dict[str, object] = {}
    if isinstance(obj, dict):
        for key, val in obj.items():
            out.update(flatten(val, f"{prefix}.{key}" if prefix else str(key)))
    elif isinstance(obj, list):
        if obj and all(isinstance(i, (str, int, float, bool)) for i in obj):
            out[prefix] = obj
        else:
            for idx, val in enumerate(obj):
                out.update(flatten(val, f"{prefix}[{idx}]"))
    else:
        out[prefix] = obj
    return out


def is_blank(val) -> bool:
    if val is None:
        return True
    if isinstance(val, str):
        return val.strip() == ""
    if isinstance(val, (list, dict)):
        return len(val) == 0
    return False


def fmt(val) -> str:
    if isinstance(val, list):
        return ", ".join(str(v) for v in val)
    if isinstance(val, bool):
        return "Yes" if val else "No"
    return str(val)


def copy_to_clipboard(text: str) -> str | None:
    """Best-effort clipboard copy. Returns the tool used, or None."""
    for cmd in (["pbcopy"], ["wl-copy"], ["xclip", "-selection", "clipboard"], ["xsel", "-ib"]):
        if shutil.which(cmd[0]):
            try:
                subprocess.run(cmd, input=text.encode(), check=True)
                return cmd[0]
            except subprocess.SubprocessError:
                continue
    return None


# ---------------------------------------------------------------------------
# sheet — the copy-paste cheat sheet
# ---------------------------------------------------------------------------

SHEET_LAYOUT: list[tuple[str, list[tuple[str, str]]]] = [
    ("IDENTITY", [
        ("Legal name", "personal.legal_first_name personal.legal_middle_name personal.legal_last_name"),
        ("Preferred name", "personal.preferred_name"),
        ("Email", "personal.email"),
        ("Phone", "personal.phone"),
        ("Pronouns", "personal.pronouns"),
    ]),
    ("ADDRESS", [
        ("Street", "personal.address.street"),
        ("Street 2", "personal.address.street2"),
        ("City", "personal.address.city"),
        ("State", "personal.address.state"),
        ("ZIP", "personal.address.zip"),
        ("Country", "personal.address.country"),
    ]),
    ("LINKS", [
        ("LinkedIn", "links.linkedin"),
        ("GitHub", "links.github"),
        ("Portfolio", "links.portfolio"),
        ("Website", "links.website"),
    ]),
    ("WORK AUTHORIZATION", [
        ("Authorized to work (US)", "work_authorization.authorized_to_work_us"),
        ("Need sponsorship NOW", "work_authorization.require_sponsorship_now"),
        ("Need sponsorship FUTURE", "work_authorization.require_sponsorship_future"),
        ("Visa status", "work_authorization.visa_status"),
    ]),
    ("LOGISTICS", [
        ("Desired salary", "logistics.desired_salary"),
        ("Salary range", "logistics.desired_salary_range"),
        ("Earliest start", "logistics.earliest_start_date"),
        ("Willing to relocate", "logistics.willing_to_relocate"),
        ("Remote preference", "logistics.remote_preference"),
        ("Willing to travel", "logistics.willing_to_travel"),
    ]),
    ("SCREENING", [
        ("Over 18", "screening.over_18"),
        ("Background check OK", "screening.consent_background_check"),
        ("Drug test OK", "screening.consent_drug_test"),
        ("Felony conviction", "screening.convicted_of_felony"),
        ("Worked here before", "screening.previously_employed_here"),
        ("How did you hear", "screening.how_did_you_hear"),
    ]),
    ("EEO (voluntary)", [
        ("Gender", "eeo.gender"),
        ("Race/ethnicity", "eeo.race_ethnicity"),
        ("Veteran status", "eeo.veteran_status"),
        ("Disability status", "eeo.disability_status"),
    ]),
]


def cmd_sheet(args) -> None:
    data = load(PROFILE)
    flat = flatten(data)
    width = 26

    print()
    print(bold("  APPLICATION CHEAT SHEET") + dim("   (./af get <field> --copy for one value)"))
    print()

    for section, rows in SHEET_LAYOUT:
        printed_any = False
        lines = []
        for label, paths in rows:
            parts = [fmt(flat.get(p, "")) for p in paths.split()]
            value = " ".join(p for p in parts if p.strip())
            if is_blank(value):
                if args.all:
                    lines.append(f"    {label:<{width}} {dim('—')}")
                continue
            printed_any = True
            lines.append(f"    {label:<{width}} {value}")
        if printed_any or args.all:
            print("  " + cyan(section))
            print("\n".join(lines))
            print()

    for job in data.get("experience", []):
        if is_blank(job.get("company")):
            continue
        end = job.get("end_date") or ("Present" if job.get("is_current") else "")
        print("  " + cyan(f"EMPLOYER — {job.get('company')}"))
        if not is_blank(job.get("title")):
            print(f"    {'Title':<{width}} {job['title']}")
        if not (is_blank(job.get("start_date")) and is_blank(end)):
            print(f"    {'Dates':<{width}} {job.get('start_date', '')} – {end}")
        if not is_blank(job.get("location")):
            print(f"    {'Location':<{width}} {job['location']}")
        for label, key in (
            ("Supervisor", "supervisor_name"),
            ("Supervisor phone", "supervisor_phone"),
            ("Supervisor email", "supervisor_email"),
            ("May contact", "may_contact"),
            ("Reason for leaving", "reason_for_leaving"),
        ):
            if not is_blank(job.get(key)):
                print(f"    {label:<{width}} {job[key]}")
        print()

    for edu in data.get("education", []):
        if is_blank(edu.get("school")):
            continue
        print("  " + cyan(f"EDUCATION — {edu.get('school')}"))
        degree = " in ".join(
            part for part in (edu.get("degree", ""), edu.get("field", "")) if not is_blank(part)
        )
        if degree:
            print(f"    {'Degree':<{width}} {degree}")
        if not (is_blank(edu.get("start_date")) and is_blank(edu.get("end_date"))):
            print(f"    {'Dates':<{width}} {edu.get('start_date', '')} – {edu.get('end_date', '')}")
        if not is_blank(edu.get("gpa")):
            print(f"    {'GPA':<{width}} {edu['gpa']}")
        print()

    refs = [r for r in data.get("references", []) if not is_blank(r.get("name"))]
    if refs:
        print("  " + cyan("REFERENCES"))
        for ref in refs:
            detail = ", ".join(
                part for part in (ref.get("title", ""), ref.get("company", "")) if not is_blank(part)
            )
            print(f"    {ref.get('name')}" + (f" — {detail}" if detail else ""))
            contact = "  ".join(
                str(part) for part in (ref.get("email", ""), ref.get("phone", "")) if not is_blank(part)
            )
            if contact:
                print(f"      {dim(contact)}")
        print()


# ---------------------------------------------------------------------------
# get — one value, for piping to the clipboard
# ---------------------------------------------------------------------------

ALIASES = {
    "email": "personal.email",
    "phone": "personal.phone",
    "first": "personal.legal_first_name",
    "last": "personal.legal_last_name",
    "name": "personal.legal_first_name personal.legal_last_name",
    "address": "personal.address.street",
    "city": "personal.address.city",
    "state": "personal.address.state",
    "zip": "personal.address.zip",
    "linkedin": "links.linkedin",
    "github": "links.github",
    "portfolio": "links.portfolio",
    "salary": "logistics.desired_salary",
    "start": "logistics.earliest_start_date",
}


def cmd_get(args) -> None:
    flat = flatten(load(PROFILE))
    key = args.field.strip()

    if key in ALIASES:
        paths = ALIASES[key].split()
        value = " ".join(fmt(flat.get(p, "")) for p in paths).strip()
    elif key in flat:
        value = fmt(flat[key])
    else:
        matches = [k for k in flat if key.lower() in k.lower()]
        if not matches:
            print(f"no field matching {key!r}", file=sys.stderr)
            print(dim("  try: ./af fields"), file=sys.stderr)
            sys.exit(1)
        if len(matches) > 1:
            print(f"{key!r} is ambiguous:", file=sys.stderr)
            for m in matches[:15]:
                print(f"  {m}", file=sys.stderr)
            sys.exit(1)
        value = fmt(flat[matches[0]])

    if is_blank(value):
        print(f"{key!r} is blank in profile.toml", file=sys.stderr)
        sys.exit(1)

    print(value)
    if args.copy:
        tool = copy_to_clipboard(value)
        msg = f"copied to clipboard ({tool})" if tool else "no clipboard tool found (install xclip/wl-clipboard)"
        print(dim(f"  {msg}"), file=sys.stderr)


def cmd_fields(args) -> None:
    flat = flatten(load(PROFILE))
    print(bold("aliases:"))
    for alias, path in sorted(ALIASES.items()):
        print(f"  {alias:<12} -> {path}")
    print()
    print(bold("all paths:"))
    for key, val in flat.items():
        mark = dim(" (blank)") if is_blank(val) else ""
        print(f"  {key}{mark}")


# ---------------------------------------------------------------------------
# export — flat JSON for autofill extensions / Claude in Chrome
# ---------------------------------------------------------------------------

def cmd_export(args) -> None:
    data = load(PROFILE)
    if args.format == "json":
        payload = json.dumps(data, indent=2, default=str)
    elif args.format == "flat":
        flat = {k: v for k, v in flatten(data).items() if not is_blank(v)}
        payload = json.dumps(flat, indent=2, default=str)
    else:  # env
        lines = []
        for key, val in flatten(data).items():
            if is_blank(val):
                continue
            name = re.sub(r"[^A-Z0-9]+", "_", key.upper())
            lines.append(f'{name}="{fmt(val)}"')
        payload = "\n".join(lines)

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(payload + "\n", encoding="utf-8")
        print(f"wrote {out}")
    else:
        print(payload)


# ---------------------------------------------------------------------------
# answer — fuzzy-match a form question to a stored answer
# ---------------------------------------------------------------------------

STOPWORDS = {
    "a", "an", "the", "is", "are", "do", "does", "did", "you", "your", "yours",
    "we", "us", "our", "i", "me", "my", "to", "for", "of", "in", "on", "at",
    "and", "or", "this", "that", "it", "be", "been", "have", "has", "with",
    "would", "like", "any", "please", "describe", "tell", "about", "what",
    "why", "how", "when", "if", "can", "will", "there", "them", "role",
    "position", "job", "company", "us",
}


def tokenize(text: str, keep_stopwords: bool = False) -> set[str]:
    words = {w for w in re.findall(r"[a-z0-9']+", text.lower()) if len(w) > 1}
    if keep_stopwords:
        return words
    return {w for w in words if w not in STOPWORDS}


def score(query: set[str], candidate: str, loose: bool = False) -> float:
    cand = tokenize(candidate, keep_stopwords=loose)
    if not cand or not query:
        return 0.0
    overlap = len(query & cand)
    if not overlap:
        return 0.0
    # Reward covering the candidate phrase; lightly penalize length mismatch.
    return overlap / len(cand | query) + 0.35 * (overlap / len(cand))


def cmd_answer(args) -> None:
    bank = load(ANSWERS).get("answers", [])
    if not bank:
        sys.exit("profile/answers.toml has no [[answers]] blocks")

    query = " ".join(args.question)
    if not query.strip():
        print(bold("stored answers:"))
        for entry in bank:
            print(f"  {cyan(entry['id']):<28} {entry.get('label', '')}")
        return

    qtokens = tokenize(query)
    loose = not qtokens
    if loose:
        qtokens = tokenize(query, keep_stopwords=True)

    ranked = []
    for entry in bank:
        phrases = list(entry.get("match", [])) + [entry.get("label", ""), entry.get("id", "")]
        best = max((score(qtokens, p, loose) for p in phrases if p), default=0.0)
        ranked.append((best, entry))
    ranked.sort(key=lambda pair: pair[0], reverse=True)

    top_score, top = ranked[0]
    if top_score < 0.15:
        print(f"no stored answer matches {query!r}", file=sys.stderr)
        print(dim("  closest:"), file=sys.stderr)
        for s, entry in ranked[:3]:
            print(dim(f"    {entry['id']}  ({s:.2f})  {entry.get('label','')}"), file=sys.stderr)
        print(dim("\n  add it: edit profile/answers.toml"), file=sys.stderr)
        sys.exit(1)

    text = top["text"].strip()
    if args.company:
        text = text.replace("{COMPANY}", args.company)
    if args.role:
        text = text.replace("{ROLE}", args.role)

    if not args.raw:
        print(dim(f"  [{top['id']}] {top.get('label', '')}  (match {top_score:.2f})"), file=sys.stderr)
        runners = [e for s, e in ranked[1:3] if s > 0.15]
        if runners:
            alts = ", ".join(e["id"] for e in runners)
            print(dim(f"  also: {alts}"), file=sys.stderr)
        print(file=sys.stderr)

    print(text)

    if "{" in text and not args.raw:
        print(file=sys.stderr)
        print(yellow("  ^ has {PLACEHOLDERS} — fill them before submitting."), file=sys.stderr)

    if args.copy:
        tool = copy_to_clipboard(text)
        if tool:
            print(dim(f"  copied to clipboard ({tool})"), file=sys.stderr)


# ---------------------------------------------------------------------------
# resume — generate a tagged variant as Markdown
# ---------------------------------------------------------------------------

def wants(item_tags, selected: set[str]) -> bool:
    """An item appears if it has no tags, or shares any selected tag."""
    tags = set(item_tags or [])
    if not tags:
        return True
    return bool(tags & selected)


def select_resume(base: dict, args) -> dict:
    """Pick the content for one variant. Rendering is a separate step."""
    selected = {t.strip().lower() for t in args.tags.split(",") if t.strip()}
    if not selected:
        selected = {"default"}

    header = base.get("header", {})
    if is_blank(header.get("name")):
        sys.exit(
            "resume/base.toml has no header.name yet.\n"
            "  Fill in resume/base.toml first — or paste your existing resume\n"
            "  into a Claude Code session and ask it to populate the file."
        )

    summaries = [s for s in base.get("summaries", []) if not is_blank(s.get("text"))]
    if args.summary:
        chosen = next((s for s in summaries if s.get("id") == args.summary), None)
        if chosen is None:
            sys.exit(f"no summary with id {args.summary!r}")
    else:
        chosen = next((s for s in summaries if wants(s.get("tags"), selected)), None)

    headline = header.get("headline", "")
    if chosen and not is_blank(chosen.get("headline")):
        headline = chosen["headline"]

    contact = [
        c for c in (
            header.get("location", ""), header.get("email", ""), header.get("phone", ""),
            header.get("linkedin", ""), header.get("github", ""), header.get("portfolio", ""),
        ) if not is_blank(c)
    ]

    jobs = []
    for job in base.get("jobs", []):
        if is_blank(job.get("company")) or not wants(job.get("tags"), selected):
            continue
        bullets = [
            b["text"].strip() for b in job.get("bullets", [])
            if not is_blank(b.get("text")) and wants(b.get("tags"), selected)
        ]
        if args.max_bullets:
            bullets = bullets[: args.max_bullets]
        meta = [m for m in (job.get("location", ""),
                            f"{job.get('start', '')} – {job.get('end') or 'Present'}")
                if not is_blank(m)]
        jobs.append({"title": job.get("title", ""), "company": job.get("company", ""),
                     "meta": meta, "bullets": bullets})

    projects = []
    for proj in base.get("projects", []):
        if is_blank(proj.get("name")) or not wants(proj.get("tags"), selected):
            continue
        projects.append({
            "name": proj["name"], "link": proj.get("link", ""),
            "description": proj.get("description", "").strip(),
            "bullets": [b["text"].strip() for b in proj.get("bullets", [])
                        if not is_blank(b.get("text")) and wants(b.get("tags"), selected)],
        })

    edus = []
    for edu in base.get("education", []):
        if is_blank(edu.get("school")) or not wants(edu.get("tags"), selected):
            continue
        extras = [e for e in (edu.get("location", ""), edu.get("end", "")) if not is_blank(e)]
        if not is_blank(edu.get("gpa")):
            extras.append(f"GPA {edu['gpa']}")
        if not is_blank(edu.get("honors")):
            extras.append(str(edu["honors"]))
        edus.append({"school": edu["school"], "degree": edu.get("degree", ""),
                     "field": edu.get("field", ""), "meta": extras})

    groups = [
        {"name": g.get("name", "Skills"), "items": g["items"]}
        for g in base.get("skill_groups", [])
        if g.get("items") and wants(g.get("tags"), selected)
    ]

    return {"name": header["name"], "headline": headline, "contact": contact,
            "summary": chosen["text"].strip() if chosen else "", "jobs": jobs,
            "projects": projects, "education": edus, "skills": groups,
            "tags": sorted(selected)}


def render_markdown(r: dict) -> str:
    out = [f"# {r['name']}"]
    if r["headline"]:
        out.append(f"**{r['headline']}**")
    if r["contact"]:
        out.append(" · ".join(r["contact"]))
    out.append("")

    if r["summary"]:
        out += ["## Summary", "", r["summary"], ""]

    if r["jobs"]:
        out += ["## Experience", ""]
        for job in r["jobs"]:
            out.append(f"### {job['title']} — {job['company']}")
            out.append(f"*{' · '.join(job['meta'])}*")
            out.append("")
            out += [f"- {b}" for b in job["bullets"]]
            out.append("")

    if r["projects"]:
        out += ["## Projects", ""]
        for proj in r["projects"]:
            out.append(f"### {proj['name']}" + (f" — {proj['link']}" if proj["link"] else ""))
            if proj["description"]:
                out.append(proj["description"])
            out.append("")
            out += [f"- {b}" for b in proj["bullets"]]
            out.append("")

    if r["education"]:
        out += ["## Education", ""]
        for edu in r["education"]:
            line = f"**{edu['school']}** — {edu['degree']}"
            if edu["field"]:
                line += f", {edu['field']}"
            out.append(line)
            if edu["meta"]:
                out.append(f"*{' · '.join(edu['meta'])}*")
            out.append("")

    if r["skills"]:
        out += ["## Skills", ""]
        for group in r["skills"]:
            out.append(f"**{group['name']}:** {', '.join(group['items'])}")
        out.append("")

    return re.sub(r"\n{3,}", "\n\n", "\n".join(out).rstrip()) + "\n"


# Deliberately plain: single column, real text, standard section names, no
# tables or text boxes. Multi-column "designer" resumes are what ATS parsers
# mangle — the layout that survives parsing is the boring one.
RESUME_CSS = """
  @page { size: letter; margin: 0.5in; }
  * { box-sizing: border-box; }
  body {
    font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
    font-size: 10.5pt; line-height: 1.42; color: #16191d;
    max-width: 7.5in; margin: 0 auto; padding: 0.5in 0.55in;
    -webkit-print-color-adjust: exact;
  }
  h1 { font-size: 20pt; margin: 0 0 2px; letter-spacing: -0.3px; }
  .headline { font-size: 11pt; font-weight: 600; color: #34383f; margin-bottom: 4px; }
  .contact { font-size: 9.5pt; color: #4a4f57; margin-bottom: 14px; }
  .contact span:not(:last-child)::after { content: " · "; color: #a6abb3; }
  h2 {
    font-size: 9.5pt; text-transform: uppercase; letter-spacing: 1.1px;
    color: #16191d; border-bottom: 1.5px solid #16191d;
    padding-bottom: 3px; margin: 16px 0 9px;
  }
  .entry { margin-bottom: 11px; page-break-inside: avoid; }
  .entry-head {
    display: flex; justify-content: space-between;
    align-items: baseline; gap: 12px;
  }
  .role { font-size: 10.5pt; font-weight: 700; }
  .meta { font-size: 9pt; color: #5b616a; white-space: nowrap; }
  ul { margin: 5px 0 0; padding-left: 17px; }
  li { margin-bottom: 3px; }
  .summary { margin-bottom: 2px; }
  .skills-row { margin-bottom: 4px; }
  .skills-row b { font-weight: 700; }
  a { color: inherit; text-decoration: none; }
  .print-hint {
    background: #fff8e1; border: 1px solid #f0d58c; border-radius: 6px;
    padding: 10px 14px; font-size: 9.5pt; color: #6b5514; margin-bottom: 20px;
  }
  @media print { .print-hint { display: none; } body { padding: 0; } }
"""


def esc(text: str) -> str:
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def render_html(r: dict) -> str:
    parts = [
        "<!DOCTYPE html>", '<html lang="en">', "<head>",
        '<meta charset="utf-8">',
        f"<title>{esc(r['name'])} — Resume</title>",
        f"<style>{RESUME_CSS}</style>", "</head>", "<body>",
        '<div class="print-hint">Press <b>Ctrl/Cmd + P</b> and choose '
        '<b>Save as PDF</b>. This box will not appear in the PDF.</div>',
        f"<h1>{esc(r['name'])}</h1>",
    ]
    if r["headline"]:
        parts.append(f'<div class="headline">{esc(r["headline"])}</div>')
    if r["contact"]:
        spans = "".join(f"<span>{esc(c)}</span>" for c in r["contact"])
        parts.append(f'<div class="contact">{spans}</div>')

    if r["summary"]:
        parts.append("<h2>Summary</h2>")
        parts.append(f'<div class="summary">{esc(r["summary"])}</div>')

    if r["jobs"]:
        parts.append("<h2>Experience</h2>")
        for job in r["jobs"]:
            role = " — ".join(x for x in (esc(job["title"]), esc(job["company"])) if x)
            parts.append('<div class="entry"><div class="entry-head">'
                         f'<span class="role">{role}</span>'
                         f'<span class="meta">{esc(" · ".join(job["meta"]))}</span></div>')
            if job["bullets"]:
                items = "".join(f"<li>{esc(b)}</li>" for b in job["bullets"])
                parts.append(f"<ul>{items}</ul>")
            parts.append("</div>")

    if r["projects"]:
        parts.append("<h2>Projects</h2>")
        for proj in r["projects"]:
            parts.append('<div class="entry"><div class="entry-head">'
                         f'<span class="role">{esc(proj["name"])}</span>'
                         f'<span class="meta">{esc(proj["link"])}</span></div>')
            if proj["description"]:
                parts.append(f'<div class="summary">{esc(proj["description"])}</div>')
            if proj["bullets"]:
                items = "".join(f"<li>{esc(b)}</li>" for b in proj["bullets"])
                parts.append(f"<ul>{items}</ul>")
            parts.append("</div>")

    if r["education"]:
        parts.append("<h2>Education</h2>")
        for edu in r["education"]:
            degree = edu["degree"] + (f", {edu['field']}" if edu["field"] else "")
            parts.append('<div class="entry"><div class="entry-head">'
                         f'<span class="role">{esc(edu["school"])}</span>'
                         f'<span class="meta">{esc(" · ".join(edu["meta"]))}</span></div>')
            if degree.strip(", "):
                parts.append(f'<div class="summary">{esc(degree)}</div>')
            parts.append("</div>")

    if r["skills"]:
        parts.append("<h2>Skills</h2>")
        for group in r["skills"]:
            parts.append(f'<div class="skills-row"><b>{esc(group["name"])}:</b> '
                         f'{esc(", ".join(group["items"]))}</div>')

    parts += ["</body>", "</html>"]
    return "\n".join(parts) + "\n"


def cmd_resume(args) -> None:
    resume = select_resume(load(RESUME_BASE), args)
    explicit = args.format is not None
    fmt_name = args.format or "md"
    out_path = args.out

    # Infer format from the output extension when it's unambiguous.
    if out_path and not explicit:
        if out_path.endswith((".html", ".htm")):
            fmt_name = "html"
        elif out_path.endswith(".md"):
            fmt_name = "md"

    text = render_html(resume) if fmt_name == "html" else render_markdown(resume)

    if not out_path:
        print(text, end="")
        return

    dest = Path(out_path)
    if not dest.is_absolute():
        dest = ROOT / dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")

    shown = dest.relative_to(ROOT) if dest.is_relative_to(ROOT) else dest
    words = len(re.sub(r"<[^>]+>", " ", text).split()) if fmt_name == "html" else len(text.split())
    print(f"wrote {shown}")
    print(dim(f"  tags: {', '.join(resume['tags'])} · {fmt_name} · ~{words} words"))
    if words > 600:
        print(yellow("  long for one page — consider --max-bullets 4"))
    if fmt_name == "html":
        print(dim(f"  open it, then Ctrl/Cmd+P -> Save as PDF"))


# ---------------------------------------------------------------------------
# init — copy the blank templates into the real (gitignored) filenames
# ---------------------------------------------------------------------------

TEMPLATES = [
    ("profile/profile.example.toml", "profile/profile.toml"),
    ("profile/answers.example.toml", "profile/answers.toml"),
    ("resume/base.example.toml", "resume/base.toml"),
    ("resume/cover-letter-base.example.md", "resume/cover-letter-base.md"),
]


def cmd_init(args) -> None:
    created, skipped = [], []
    for src_rel, dst_rel in TEMPLATES:
        src, dst = ROOT / src_rel, ROOT / dst_rel
        if not src.exists():
            continue
        if dst.exists() and not args.force:
            skipped.append(dst_rel)
            continue
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        created.append(dst_rel)

    print()
    for path in created:
        print("  " + green("created") + f"  {path}")
    for path in skipped:
        print("  " + dim(f"exists   {path}  (--force to overwrite)"))
    print()

    if created:
        print("  These files are " + bold("gitignored") + " — they hold your personal data")
        print("  and this repo is public. Nothing here gets committed.")
        print()
        print("  Next:")
        print("    1. fill in " + cyan("profile/profile.toml"))
        print("    2. " + cyan("./af doctor") + "   to see what's still blank")
        print("    3. " + cyan("./af sheet") + "    when you're filling out a form")
        print()
        print(dim("  Faster: open this repo in Claude Code, paste your existing"))
        print(dim("  profile doc or resume, and ask it to fill the files in for you."))
        print()


def git_tracked(path: Path) -> bool:
    """True if git is tracking this file — i.e. it would be pushed."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(path.relative_to(ROOT))],
            cwd=ROOT, capture_output=True, check=False,
        )
        return result.returncode == 0
    except (OSError, ValueError):
        return False


# ---------------------------------------------------------------------------
# doctor — what's still blank, and where your files disagree
# ---------------------------------------------------------------------------

# Fields ATS forms ask for often enough that a blank will stall you mid-application.
CRITICAL = [
    "personal.legal_first_name", "personal.legal_last_name", "personal.email",
    "personal.phone", "personal.address.city", "personal.address.state",
    "personal.address.zip", "links.linkedin",
    "work_authorization.authorized_to_work_us",
    "work_authorization.require_sponsorship_now",
    "work_authorization.require_sponsorship_future",
    "logistics.desired_salary_range", "logistics.earliest_start_date",
    "logistics.remote_preference", "screening.how_did_you_hear",
    "eeo.gender", "eeo.race_ethnicity", "eeo.veteran_status", "eeo.disability_status",
]


def cmd_doctor(args) -> None:
    data = load(PROFILE)
    flat = flatten(data)
    problems = 0

    print()
    exposed = [f for f in (PROFILE, ANSWERS, RESUME_BASE, LOG_CSV)
               if f.exists() and git_tracked(f)]
    if exposed:
        print("  " + red("PERSONAL DATA IS TRACKED BY GIT"))
        for path in exposed:
            print(f"    {path.relative_to(ROOT)}")
        print("  " + dim("  These hold your address, phone and your references' contacts."))
        print("  " + dim("  Untrack them:  git rm --cached <file>"))
        print("  " + dim("  (Safe to ignore only if this repo is private.)"))
        print()

    missing = [k for k in CRITICAL if is_blank(flat.get(k))]
    if missing:
        problems += len(missing)
        print("  " + red(f"{len(missing)} commonly-required field(s) still blank"))
        for key in missing:
            print(f"    {key}")
        print()
    else:
        print("  " + green("all commonly-required fields are filled"))
        print()

    jobs = [j for j in data.get("experience", []) if not is_blank(j.get("company"))]
    if not jobs:
        problems += 1
        print("  " + red("no employment history") + dim("  — add [[experience]] blocks"))
        print()
    else:
        gaps = []
        for job in jobs:
            for key, label in (
                ("supervisor_name", "supervisor name"),
                ("supervisor_phone", "supervisor phone"),
                ("may_contact", "may-we-contact"),
                ("reason_for_leaving", "reason for leaving"),
            ):
                if is_blank(job.get(key)):
                    gaps.append(f"{job['company']}: {label}")
        if gaps:
            problems += len(gaps)
            print("  " + yellow(f"{len(gaps)} employer detail(s) missing") +
                  dim("  — Workday/Taleo ask for these"))
            for gap in gaps:
                print(f"    {gap}")
            print()

    if not [e for e in data.get("education", []) if not is_blank(e.get("school"))]:
        problems += 1
        print("  " + yellow("no education entries"))
        print()

    refs = [r for r in data.get("references", []) if not is_blank(r.get("name"))]
    if len(refs) < 3:
        problems += 1
        print("  " + yellow(f"{len(refs)} reference(s)") + dim("  — most forms ask for 3"))
        print()

    # Cross-check: resume and profile must tell the same employment story.
    if RESUME_BASE.exists():
        base = load(RESUME_BASE)
        rjobs = {
            (j.get("company", "").strip().lower(), j.get("title", "").strip().lower())
            for j in base.get("jobs", []) if not is_blank(j.get("company"))
        }
        pjobs = {
            (j.get("company", "").strip().lower(), j.get("title", "").strip().lower())
            for j in jobs
        }
        only_resume = rjobs - pjobs
        only_profile = pjobs - rjobs
        if only_resume or only_profile:
            problems += 1
            print("  " + yellow("resume/base.toml and profile.toml disagree on employment") +
                  dim("  — background checks catch this"))
            for company, title in sorted(only_resume):
                print(f"    resume only:  {company} / {title}")
            for company, title in sorted(only_profile):
                print(f"    profile only: {company} / {title}")
            print()

    answers = load(ANSWERS).get("answers", []) if ANSWERS.exists() else []
    unfilled = [a["id"] for a in answers if "{" in a.get("text", "")]
    if unfilled:
        print("  " + dim(f"{len(unfilled)} answer(s) still contain "
                         f"{{PLACEHOLDERS}}: {', '.join(unfilled)}"))
        print("  " + dim("  (that's fine — placeholders mark what to personalize per job)"))
        print()

    if problems == 0:
        print("  " + green("profile is application-ready.") + "  " + dim("./af sheet"))
    else:
        print(dim(f"  {problems} item(s) to fill in — profile/profile.toml"))
    print()


# ---------------------------------------------------------------------------
# log — application tracker
# ---------------------------------------------------------------------------

LOG_FIELDS = [
    "id", "date_applied", "company", "role", "location", "source", "url",
    "status", "resume_variant", "contact", "salary_posted", "last_touch", "notes",
]

STATUSES = ["applied", "screening", "interview", "offer", "rejected", "ghosted", "withdrawn"]
OPEN_STATUSES = {"applied", "screening", "interview"}


def read_log() -> list[dict]:
    if not LOG_CSV.exists():
        return []
    with LOG_CSV.open(newline="", encoding="utf-8") as fh:
        return [dict(row) for row in csv.DictReader(fh)]


def write_log(rows: list[dict]) -> None:
    LOG_CSV.parent.mkdir(parents=True, exist_ok=True)
    with LOG_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=LOG_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in LOG_FIELDS})


def today() -> str:
    return dt.date.today().isoformat()


def days_since(iso: str) -> int | None:
    try:
        return (dt.date.today() - dt.date.fromisoformat(iso)).days
    except (ValueError, TypeError):
        return None


def cmd_log_add(args) -> None:
    rows = read_log()
    next_id = max((int(r["id"]) for r in rows if str(r.get("id", "")).isdigit()), default=0) + 1
    row = {
        "id": str(next_id),
        "date_applied": args.date or today(),
        "company": args.company,
        "role": args.role,
        "location": args.location or "",
        "source": args.source or "",
        "url": args.url or "",
        "status": args.status,
        "resume_variant": args.variant or "",
        "contact": args.contact or "",
        "salary_posted": args.salary or "",
        "last_touch": args.date or today(),
        "notes": args.notes or "",
    }
    rows.append(row)
    write_log(rows)
    print(f"#{next_id}  {args.company} — {args.role}  [{args.status}]")


def cmd_log_list(args) -> None:
    rows = read_log()
    if not rows:
        print(dim("  no applications logged yet — ./af log add --company X --role Y"))
        return
    if args.status:
        rows = [r for r in rows if r.get("status") == args.status]
    elif args.open:
        rows = [r for r in rows if r.get("status") in OPEN_STATUSES]
    if args.company:
        needle = args.company.lower()
        rows = [r for r in rows if needle in r.get("company", "").lower()]

    rows.sort(key=lambda r: r.get("date_applied", ""), reverse=True)
    if not rows:
        print(dim("  nothing matches that filter"))
        return

    print()
    for row in rows:
        age = days_since(row.get("date_applied", ""))
        age_s = f"{age}d ago" if age is not None else ""
        status = row.get("status", "")
        colored = {
            "offer": green, "interview": green, "screening": cyan,
            "rejected": dim, "ghosted": dim, "withdrawn": dim,
        }.get(status, lambda s: s)(status)
        print(f"  {dim('#' + str(row.get('id', ''))):<6} {row.get('company', ''):<26} "
              f"{row.get('role', '')[:34]:<34} {colored:<12} {dim(age_s)}")
    print()
    print(dim(f"  {len(rows)} shown"))
    print()


def cmd_log_status(args) -> None:
    rows = read_log()
    target = next((r for r in rows if r.get("id") == str(args.id)), None)
    if target is None:
        sys.exit(f"no application with id {args.id}")
    old = target.get("status", "")
    target["status"] = args.status
    target["last_touch"] = today()
    if args.notes:
        existing = target.get("notes", "")
        target["notes"] = f"{existing} | {args.notes}".strip(" |")
    write_log(rows)
    print(f"#{args.id}  {target.get('company')} — {target.get('role')}: {old} -> {args.status}")


def cmd_log_due(args) -> None:
    """Applications worth a follow-up nudge."""
    rows = [r for r in read_log() if r.get("status") in OPEN_STATUSES]
    due = []
    for row in rows:
        age = days_since(row.get("last_touch") or row.get("date_applied", ""))
        if age is not None and age >= args.days:
            due.append((age, row))
    due.sort(key=lambda pair: pair[0], reverse=True)

    print()
    if not due:
        print("  " + green(f"nothing older than {args.days} days without a touch"))
        print()
        return
    print("  " + bold(f"{len(due)} application(s) worth a follow-up"))
    print()
    for age, row in due:
        print(f"  {dim('#' + str(row.get('id', ''))):<6} {row.get('company', ''):<26} "
              f"{row.get('role', '')[:30]:<30} {yellow(str(age) + 'd')} "
              f"{dim(row.get('contact', '') or 'no contact saved')}")
    print()
    print(dim("  mark one touched: ./af log status <id> <status> --notes 'followed up'"))
    print()


def cmd_log_stats(args) -> None:
    rows = read_log()
    if not rows:
        print(dim("  no applications logged yet"))
        return
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.get("status", "?")] = counts.get(row.get("status", "?"), 0) + 1
    total = len(rows)

    def age_or_old(row: dict) -> int:
        age = days_since(row.get("date_applied", ""))
        return 999 if age is None else age  # 0 is falsy — don't use `or` here

    recent = [r for r in rows if age_or_old(r) <= 7]
    responded = sum(counts.get(s, 0) for s in ("screening", "interview", "offer"))

    print()
    print(f"  {bold(str(total))} applications  ·  {bold(str(len(recent)))} in the last 7 days")
    print()
    for status in STATUSES:
        if counts.get(status):
            bar = "█" * min(counts[status], 40)
            print(f"  {status:<12} {counts[status]:>3}  {dim(bar)}")
    print()
    if total >= 10:
        rate = 100 * responded / total
        print(f"  response rate  {bold(f'{rate:.0f}%')}  {dim('(screening + interview + offer)')}")
        if rate < 5:
            print(dim("  under 5% usually means the resume isn't matching the postings,"))
            print(dim("  not that you need to apply to more. Tailor harder, apply less."))
        print()


# ---------------------------------------------------------------------------
# cli
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="af",
        description="Job application toolkit — one profile, many fast outputs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  ./af init                                first run — create your files
  ./af doctor                              what's still blank
  ./af sheet                               cheat sheet while filling a form
  ./af get email --copy                    one value onto the clipboard
  ./af answer "why do you want to work here"
  ./af resume --tags backend,python --out resume/variants/backend.md
  ./af resume --tags backend --out resume/variants/backend.html   (-> print to PDF)
  ./af export --format flat --out build/profile.json
  ./af log add --company Stripe --role "Backend Engineer" --source linkedin
  ./af log due                             who to follow up with
  ./af log stats                           response rate
""",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="create your personal files from the templates")
    p_init.add_argument("--force", action="store_true", help="overwrite existing files")
    p_init.set_defaults(func=cmd_init)

    p_sheet = sub.add_parser("sheet", help="print the copy-paste cheat sheet")
    p_sheet.add_argument("--all", action="store_true", help="include blank fields")
    p_sheet.set_defaults(func=cmd_sheet)

    p_get = sub.add_parser("get", help="print one profile value")
    p_get.add_argument("field", help="alias (email) or dotted path (personal.address.zip)")
    p_get.add_argument("--copy", action="store_true", help="also copy to clipboard")
    p_get.set_defaults(func=cmd_get)

    p_fields = sub.add_parser("fields", help="list every available field path")
    p_fields.set_defaults(func=cmd_fields)

    p_answer = sub.add_parser("answer", help="reusable answer for a free-text question")
    p_answer.add_argument("question", nargs="*", help="the question as the form words it")
    p_answer.add_argument("--company", help="substitute into {COMPANY}")
    p_answer.add_argument("--role", help="substitute into {ROLE}")
    p_answer.add_argument("--copy", action="store_true")
    p_answer.add_argument("--raw", action="store_true", help="answer only, no commentary")
    p_answer.set_defaults(func=cmd_answer)

    p_export = sub.add_parser("export", help="export the profile as JSON or env vars")
    p_export.add_argument("--format", choices=["json", "flat", "env"], default="flat")
    p_export.add_argument("--out", help="write to this path instead of stdout")
    p_export.set_defaults(func=cmd_export)

    p_resume = sub.add_parser("resume", help="generate a tailored resume variant")
    p_resume.add_argument("--tags", default="default", help="comma-separated tags to include")
    p_resume.add_argument(
        "--format", choices=["md", "html"], default=None,
        help="md (default), or html for a print-ready page you save as PDF. "
             "Inferred from --out's extension when not given.",
    )
    p_resume.add_argument("--summary", help="summary id to use")
    p_resume.add_argument("--max-bullets", type=int, help="cap bullets per job")
    p_resume.add_argument("--out", help="write to this path instead of stdout")
    p_resume.set_defaults(func=cmd_resume)

    p_doctor = sub.add_parser("doctor", help="report blank fields and inconsistencies")
    p_doctor.set_defaults(func=cmd_doctor)

    p_log = sub.add_parser("log", help="track applications")
    log_sub = p_log.add_subparsers(dest="log_command", required=True)

    l_add = log_sub.add_parser("add", help="log a new application")
    l_add.add_argument("--company", required=True)
    l_add.add_argument("--role", required=True)
    l_add.add_argument("--location")
    l_add.add_argument("--source", help="linkedin / referral / company site")
    l_add.add_argument("--url")
    l_add.add_argument("--status", default="applied", choices=STATUSES)
    l_add.add_argument("--variant", help="which resume variant you sent")
    l_add.add_argument("--contact", help="recruiter or hiring manager")
    l_add.add_argument("--salary", help="posted range")
    l_add.add_argument("--date", help="YYYY-MM-DD (defaults to today)")
    l_add.add_argument("--notes")
    l_add.set_defaults(func=cmd_log_add)

    l_list = log_sub.add_parser("list", help="list applications")
    l_list.add_argument("--status", choices=STATUSES)
    l_list.add_argument("--open", action="store_true", help="only applied/screening/interview")
    l_list.add_argument("--company", help="filter by company substring")
    l_list.set_defaults(func=cmd_log_list)

    l_status = log_sub.add_parser("status", help="update an application's status")
    l_status.add_argument("id")
    l_status.add_argument("status", choices=STATUSES)
    l_status.add_argument("--notes")
    l_status.set_defaults(func=cmd_log_status)

    l_due = log_sub.add_parser("due", help="applications worth a follow-up")
    l_due.add_argument("--days", type=int, default=7)
    l_due.set_defaults(func=cmd_log_due)

    l_stats = log_sub.add_parser("stats", help="counts and response rate")
    l_stats.set_defaults(func=cmd_log_stats)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except BrokenPipeError:  # e.g. `./af fields | head`
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        return 0
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
