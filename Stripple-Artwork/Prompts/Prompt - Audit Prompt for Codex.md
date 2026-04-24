What this prompt is
Use this in Codex to review code that Claude Code just wrote.
Always audit before marking a layer complete or moving on.

When to use it
After Claude Code finishes building a feature or completes a layer.
Copy the relevant file paths from the handoff note or build log
and paste them into the prompt below.

How to use it
1. Open Codex
2. Paste the prompt below
3. Replace the file paths placeholder with the actual file paths
   from your handoff note or build log
4. Save the audit result to your Audit Reports folder in Obsidian

---

THE PROMPT TO PASTE INTO CODEX:

Please audit the following files that were just written by another
AI coding agent:

(replace this line with the actual file paths from your notes)

I need you to review specifically for:

1. Security vulnerabilities
   Anything that could be exploited or expose user data. This
   includes things like missing ownership checks, unsafe file
   handling, tokens stored in the wrong place, or any of the
   DO NOT rules from the original architecture being violated.

2. Logic errors
   Anything that would not work as intended. Code that looks
   correct but would produce wrong results or fail in certain
   situations.

3. Missing error handling
   Situations the code does not account for. What happens if
   the database is unavailable, a file does not exist, a user
   sends unexpected input, or a background job crashes.

4. Best practice violations
   Anything a senior developer would flag in a code review.
   This includes code that works but is fragile, hard to
   maintain, or likely to cause problems as the app grows.

Format your response exactly like this:

CRITICAL ISSUES - must fix before moving on
(list each issue with a plain English explanation of what the
problem is, why it matters, and which file it is in)

MODERATE ISSUES - should fix soon
(list each issue with a plain English explanation)

MINOR ISSUES - worth addressing when time allows
(list each issue with a plain English explanation)

LOOKS GOOD - things done well
(list specific things that were implemented correctly,
especially any security or architecture requirements
that were handled properly)

Explain every issue in plain English, not just technical
jargon. Assume the person reading this is not a developer.