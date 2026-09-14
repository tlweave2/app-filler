---
name: import-profile
description: Fill profile.toml, answers.toml, or resume/base.toml from an existing resume, profile document, or LinkedIn export that the user pastes or points at. Use when the user says they already have a resume or a filled-in profile doc and wants it loaded into this repo.
---

# Import an existing profile or resume

The user already has the information. The job is to move it into this repo's
files accurately — not to improve it, and not to invent anything.

## Steps

1. **Get the source.** They'll paste it, or give a path. If they mention a file
   on their own machine and you're in a remote session, ask them to paste the
   contents — you can't read their local disk from here.

2. **Run `./af init`** if `profile/profile.toml` doesn't exist yet.

3. **Fill `profile/profile.toml`.** Map what you find onto the existing fields.
   - Keep the file's structure, comments, and field order intact. Edit values only.
   - Use `[[experience]]` / `[[education]]` / `[[references]]` blocks — duplicate
     the whole block for each additional entry.
   - Dates as `YYYY-MM`.
   - **Leave a field blank rather than guessing.** A wrong supervisor phone is
     worse than an empty one — the user will notice an empty field when
     `./af doctor` reports it, but a wrong value silently goes onto a form.

4. **Fill `resume/base.toml`.** Every bullet from every version of their resume
   goes in, tagged. This is a library, not a page — more is better here.
   - Tag by role type (`backend`, `data`, `frontend`, `management`) and by
     theme (`performance`, `leadership`, `python`).
   - A bullet that appears on two different resumes gets both tags.
   - Keep their wording. If a bullet has no metric, flag it to the user at the
     end rather than inventing a number.

5. **Check `resume/base.toml` and `profile/profile.toml` agree** on company
   names, titles, and dates. `./af doctor` cross-checks this — run it.

6. **Report back:** what you filled, what you left blank and why, and any
   bullets that could use a metric.

## Rules

- Never invent employment, dates, degrees, metrics, or contact details.
- Don't "improve" a job title. Titles get verified in background checks.
- Don't commit these files — they're gitignored, and this repo is public.
