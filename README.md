# app-filler

Apply to jobs faster by never re-entering the same information twice.

Fill in one profile. Everything else — the cheat sheet you keep open while
filling a form, tailored resume variants, reusable answers to the free-text
questions, the application tracker — generates from it.

```
./af init          # create your files from the templates
./af doctor        # what's still blank
./af sheet         # keep this open while you fill out a form
```

No dependencies. Python 3.11+ (`pip install tomli` if you're on 3.9 or 3.10).

---

## ⚠️ This repo is public

Your address, phone, salary history and your references' contact details are
**gitignored and never committed**. Only blank templates are tracked.

`./af doctor` warns you if one of those files ever becomes git-tracked.

If you'd rather have your profile synced across machines, make the repo private
first (**Settings → General → Danger Zone → Change visibility**), then remove
the top block from `.gitignore`.

---

## Setup

```bash
./af init
```

Creates `profile/profile.toml`, `profile/answers.toml`, `resume/base.toml` and
`resume/cover-letter-base.md` from the templates.

Then fill in `profile/profile.toml`. It has every field ATS forms ask for,
including the ones people forget and then spend twenty minutes digging for:
supervisor phone numbers, reason for leaving, exact employment dates, EEO
answers you'd otherwise re-decide every time.

**The fast way to fill it:** open this repo in Claude Code, paste your existing
resume or profile doc, and say "load this into profile.toml and base.toml."

Then:

```bash
./af doctor
```

It lists what's blank, flags employer details that Workday and Taleo will
demand, and cross-checks that your resume and profile tell the same employment
story — a discrepancy there is a real rejection reason at the background-check
stage.

---

## The daily loop

### While filling out a form

```bash
./af sheet                 # everything, grouped, in one screen
./af get phone --copy      # one value straight to the clipboard
./af get zip --copy
```

`./af fields` lists every available field path.

### The free-text boxes

The questions that actually cost time — "why do you want to work here", "explain
any gaps in employment", "salary expectations":

```bash
./af answer "why are you interested in this role?"
./af answer "what are your salary expectations" --copy
```

Matches on meaning, not exact wording. Answers live in `profile/answers.toml`
and ship with `{PLACEHOLDERS}` marking the one or two sentences you should
personalize per company. That's deliberate: a stock answer with one specific
sentence swapped in beats a stock answer, and beats a blank box by a mile.

### Tailoring a resume

`resume/base.toml` holds **every** bullet you could use, each tagged. A variant
is a tag selection, not a rewrite:

```bash
./af resume --tags backend,performance --out resume/variants/stripe.html
./af resume --tags data --max-bullets 4 --out resume/variants/databricks.md
```

**To get an uploadable PDF:** write a `.html` variant, open it in your browser,
then Ctrl/Cmd + P → Save as PDF. The print stylesheet is Letter-sized with
proper margins, and the yellow hint box doesn't appear in the PDF.

The layout is deliberately plain — single column, real text, standard section
headings, no tables or text boxes. Multi-column "designer" resumes are what ATS
parsers mangle; the layout that survives parsing is the boring one.

Format is inferred from the extension, or set it with `--format md|html`.

Write more bullets in the base than fit on one page — that's the point. A
bullet cut from one variant is the lead bullet of another. Each `[[summaries]]`
block can carry its own `headline`, so a data-role resume isn't titled "Senior
Backend Engineer".

In Claude Code, paste a posting and say "tailor my resume for this" — it reads
the posting, picks the tags, checks for gaps, and drafts the cover letter.

### Tracking

```bash
./af log add --company Stripe --role "Backend Engineer" --source linkedin
./af log status 12 interview --notes "phone screen Tuesday"
./af log due                 # who to follow up with
./af log stats               # counts and response rate
```

Plain CSV in `applications/log.csv`. Opens in Excel or Sheets.

### Autofill extensions

```bash
./af export --format flat --out build/profile.json
```

Flat JSON for feeding Simplify, Teal, or Claude in Chrome. `--format json`
keeps the nested structure; `--format env` gives shell variables.

---

## What actually saves time

Ranked by how much they matter, from someone else's data and plain arithmetic:

1. **The profile doc.** Re-entering the same twenty fields is most of the clock
   time in an application. Fill it once, properly, including the supervisor
   phone numbers.
2. **Tailoring, not volume.** If your response rate is under ~5%, more
   applications won't fix it — the resume isn't matching the postings.
   `./af log stats` will tell you which problem you have.
3. **Batching.** Two or three focused hours a few days a week beats
   one-at-a-time all day. Context-switching into an application costs more than
   the application does.
4. **A browser autofill extension** for Greenhouse/Lever/Workday. Simplify and
   Teal both work; so does Claude in Chrome, with you watching.

## What this doesn't do

It doesn't auto-submit applications, and it doesn't try to look human to
anti-bot systems. Two reasons, both practical: mass machine-filled applications
get filtered out at the other end, and account restrictions land on the person
whose job search depends on the account.

This is built to make *you* fast, with you in the loop.

---

## Commands

| Command | What it does |
|---|---|
| `./af init` | create your personal files from the templates |
| `./af doctor` | blank fields, missing details, inconsistencies |
| `./af sheet` | the copy-paste cheat sheet |
| `./af get <field>` | one value (`--copy` for clipboard) |
| `./af fields` | list every field path |
| `./af answer "<question>"` | reusable answer for a free-text box |
| `./af resume --tags <tags>` | generate a tailored resume variant (`.md` or `.html` → PDF) |
| `./af export` | JSON / env export for autofill tools |
| `./af log add\|list\|status\|due\|stats` | application tracker |

Run `./af <command> --help` for options.
