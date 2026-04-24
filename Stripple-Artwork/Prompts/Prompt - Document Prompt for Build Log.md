What this prompt is
Use this in Claude (claude.ai) at the end of a completed session
to generate a clean build log entry ready to paste into Obsidian.

When to use it
After a layer or feature is fully complete, audited, and fixed.
Fill in the four pieces of information listed below before pasting.

How to use it
1. Gather these four things from your session:
   - What feature or layer was built
   - What approach or key decisions were made
   - What Codex found in the audit
   - What fixes were applied
2. Open Claude at claude.ai
3. Paste the prompt below with those four things filled in
4. Copy the output and paste it as a new note in your
   Build Log folder in Obsidian
5. Use this as the note title:
   Build Log - Layer N - Name - (date)

---

THE PROMPT TO PASTE INTO CLAUDE:

I just completed a development session on my SaaS app and need
a clean build log entry for my Obsidian project vault.

Here is what happened this session:

Feature or layer built:
(describe what was built in plain English)

Approach used:
(briefly describe the key technical approach or any decisions
that were made during the session)

Codex audit findings:
(paste or summarize what Codex found - if nothing was found
write: Codex found no issues)

Fixes applied:
(list what was fixed based on the audit - if nothing needed
fixing write: No fixes required)

Please write a clean build log entry I can paste directly into
my Obsidian vault. Use this exact format and do not use any
special characters, symbols, or markdown formatting. Plain text
only so it pastes cleanly into Obsidian.

Build Session - (todays date)
Layer: (layer number and name)

---

Summary
(3 to 4 sentences in plain English describing what was built
and the current state of that part of the app)

---

Decisions Made
(list any technical or architectural decisions made this session
with a brief plain English explanation of why)

---

Issues Found and Resolved
(list what Codex found and what was fixed, in plain English.
If nothing was found write: No issues found in audit)

---

Current Status
(one clear sentence on where things stand right now)

---

Next Steps
(what happens in the next session - be specific about which
layer or feature comes next)