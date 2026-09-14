---
name: log-application
description: Log a job application, update its status, or review the pipeline and follow-ups. Use when the user says they applied somewhere, heard back, got rejected, or asks what they should follow up on.
---

# Track applications

The log is `applications/log.csv` — plain CSV, gitignored, opens in any
spreadsheet.

## Commands

```
./af log add --company X --role Y --source linkedin --variant backend --url ...
./af log list --open              # applied / screening / interview
./af log status 12 interview --notes "phone screen Tuesday"
./af log due --days 7             # worth a nudge
./af log stats                    # counts and response rate
```

Statuses: `applied`, `screening`, `interview`, `offer`, `rejected`, `ghosted`,
`withdrawn`.

## When the user mentions an application

- **"I applied to X"** → `log add`. Ask for anything missing that's cheap to
  capture now (source, posted salary, recruiter name) and skip what isn't.
- **"X got back to me"** → `log status`. Put the detail in `--notes`.
- **"who should I follow up with?"** → `log due`, then offer to draft the
  follow-up note. Keep those to three sentences.

## Reading the numbers

`./af log stats` shows a response rate once there are 10+ applications.

Under ~5% usually means the resume isn't matching the postings — the fix is
tailoring harder, not applying more. Say that plainly if the numbers show it;
volume is the more tempting response and the wrong one.

A run of `ghosted` is normal and not a signal about the user. Say so if they
seem to be reading it that way.
