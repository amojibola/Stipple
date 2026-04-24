What this prompt is
Use this in Claude Code after receiving audit results from Codex.
It tells Claude Code exactly what to fix and how to report back.

When to use it
After you have the Codex audit results and there are issues to fix.
If Codex found no critical or moderate issues you can skip this
and move on.

How to use it
1. Copy the full Codex audit results
2. Open Claude Code
3. Paste the prompt below with the issues filled in
4. After Claude Code finishes paste the summary into your
   Audit Reports note under FIXES APPLIED

---

THE PROMPT TO PASTE INTO CLAUDE CODE:

The following code was just audited by a second AI agent and
found these issues. Please address every issue in order of
severity starting with critical, then moderate, then minor.

Rules:
Do not rewrite the whole feature.
Do not proceed to the next layer.
Do not add unrelated features.
Do not change the tech stack.
Do not weaken any existing security protection.
Do not expose storage_key or internal file paths in any response.
Do not use the original uploaded filename.
Do not serve uploads directly through Nginx.
Keep fixes limited to the current layer unless a dependency
file must be changed.

For each fix do the following three things:
1. Tell me in plain English what the problem was and why it
   mattered
2. Tell me exactly what you changed to fix it including the
   file name and what was added, removed, or changed
3. Confirm the fix does not break any other part of the feature

After making the fixes, run whatever local verification is
appropriate and tell me exactly what was run and what passed.

Do not skip any issues. Address each one separately and clearly.

After all fixes are complete give me:
1. A plain English summary of what was fixed
2. The exact list of files that were modified during the fixes
3. The verification commands and tests that were run
4. Any issue that could not be fully fixed and why
5. Your assessment of whether the production readiness score
   should now be 7 or above

Do not proceed to the next layer.

---

CRITICAL ISSUES
(paste critical issues here)

MODERATE ISSUES
(paste moderate issues here)

MINOR ISSUES
(paste minor issues here)