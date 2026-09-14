# app-filler

Tooling to make job applications faster. One profile is the source of truth;
everything else generates from it.

## This repo is PUBLIC

`profile/profile.toml`, `profile/answers.toml`, `resume/base.toml`,
`resume/cover-letter-base.md`, `resume/variants/` and `applications/log.csv`
hold personal data — home address, phone, salary history, and references'
contact details. They are gitignored and **must never be committed**.

Only the `*.example.*` templates and the tooling are tracked. `./af doctor`
warns if a personal file becomes git-tracked.

When helping in this repo: never `git add -f` a personal file, and never paste
the contents of one into a commit message, PR body, or issue.

## Layout

```
af                          launcher -> tools/af.py
tools/af.py                 the CLI (stdlib only, Python 3.11+)
profile/profile.toml        master profile: everything forms ask for
profile/answers.toml        reusable answers to free-text questions
resume/base.toml            every bullet, tagged; variants are generated from it
resume/variants/            generated resumes
applications/log.csv        application tracker
```

## Commands

```
./af init                   create personal files from templates
./af doctor                 what's blank, what's inconsistent
./af sheet                  cheat sheet while filling a form
./af get email --copy       one value to the clipboard
./af answer "why us"        reusable answer for a free-text box
./af resume --tags backend --out resume/variants/x.html   # .md or .html
./af export --format flat   JSON for autofill extensions
./af log add|list|status|due|stats
```

## Conventions

- Dates are `YYYY-MM` in profile and resume files.
- A blank string means "not filled in yet" — `./af doctor` reports these.
- Resume bullets carry `tags`; a variant is a tag selection, never a rewrite.
- `af resume` renders Markdown or print-ready HTML (format inferred from the
  `--out` extension). HTML is the uploadable path: open it, print to PDF. Keep
  the layout single-column and text-only — ATS parsers mangle anything else.
- `profile.toml` and `resume/base.toml` must agree on company names, titles and
  dates. Background checks catch discrepancies; `./af doctor` cross-checks them.

## Ground rules when helping with applications

- **Never invent** experience, metrics, dates, degrees, or skills. Reframing
  what exists is the work; fabricating is not.
- Tell the user plainly when they're not a fit for a posting, and what's
  missing. Applying anyway is their decision.
- This toolkit assists a human filling forms. It does not auto-submit
  applications and does not work around bot detection — mass machine-filled
  applications get filtered out anyway, and the account risk lands on the
  person whose job search depends on it.

## Testing

No test framework. Verify changes by running the commands against a filled-in
profile — copy the repo to a scratch directory, populate it with dummy data,
and exercise each subcommand.
