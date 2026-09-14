---
name: tailor-resume
description: Tailor a resume and draft a cover letter for a specific job posting, then log the application. Use when the user pastes a job posting or job URL and wants to apply, or asks to tailor their resume for a role.
---

# Tailor a resume to a posting

This is the part of applying that actually moves response rate. Everything else
in this repo is about saving time; this is about the outcome.

## Steps

1. **Read the posting.** The user pastes it or gives a URL. Pull out:
   - The 3-5 requirements stated first or repeated — those are the real ones.
   - Exact vocabulary (some ATS keyword filters are literal: "platform
     reliability" ≠ "uptime engineering").
   - Seniority, team, and what the role actually owns day to day.

2. **Read `resume/base.toml`.** Find the bullets that match those requirements.

3. **Pick tags and generate:**
   ```
   ./af resume --tags backend,performance --out resume/variants/<company>-<role>.md
   ```
   Check the output is one page (`af resume` warns past ~600 words). Trim with
   `--max-bullets 4` or a narrower tag set.

4. **If the base is genuinely missing a relevant bullet**, ask the user about
   the experience, then add it to `resume/base.toml` with tags — so it's
   available for every future application, not just this one. This is how the
   base gets better over time.

5. **Order matters more than content.** The bullet that matches the posting's
   top requirement goes first under each job. A recruiter reads the first
   bullet of each role and skims the rest.

6. **Draft the cover letter** from `resume/cover-letter-base.md` if the posting
   asks for one, or if the role is a stretch. Fill every `{PLACEHOLDER}`.
   The hook sentence must name something specific and real about the company —
   if you can't find anything concrete, say so rather than writing filler.

7. **Log it:**
   ```
   ./af log add --company X --role Y --source linkedin --variant <tags> --url ...
   ```

## Rules

- **Never invent experience, metrics, or skills.** Reframing what's in
  `base.toml` is the job; adding what isn't there is lying on a job
  application, and it surfaces in the interview.
- If the user isn't a plausible fit, say so plainly and say what's missing.
  Applying anyway is their call — but they should know before spending the time.
- Don't pad to fill a page. A short resume that matches beats a long one.
- Flag keyword gaps you can't honestly close: "the posting wants Kubernetes and
  nothing in your base mentions it" is useful information.
