What this prompt is
Paste this into Claude Code before closing any session that ends
in the middle of a layer or at the end of a completed layer.
It generates a handoff note you save in your status block so
the next session knows exactly where to pick up.

When to use it
At the end of every single Claude Code session without exception.
It takes two minutes and prevents losing context between sessions.

How to use it
Paste the prompt below as your last message before closing
Claude Code. Save the output to your Obsidian note titled:
Prompt - Current Project Status Block
under the MID-LAYER HANDOFF section at the bottom.

---

THE PROMPT TO PASTE INTO CLAUDE CODE:

Before we end this session please give me a detailed handoff
note so the next session can pick up exactly where we stopped.

Write it in plain English with no special characters, symbols,
or markdown formatting.

Cover all of the following:

WHAT WAS COMPLETED THIS SESSION
List every file that was created or modified with the full
file path. For each file describe in one sentence what it does.

WHAT IS FULLY WORKING RIGHT NOW
List every endpoint, feature, or component that is complete
and verified working. Be specific.

WHAT IS PARTIALLY BUILT
List anything that was started but not finished. For each one
describe what was done and what still needs to happen.

WHAT HAS NOT BEEN STARTED YET
List everything in the current layer that has not been touched.

DECISIONS MADE THIS SESSION
List any technical decisions made during this session that were
not in the original briefing document. Include what was decided
and why.

PROBLEMS ENCOUNTERED
List any problems that came up and exactly how they were resolved.
Include the problem, the cause, and the fix.

SECURITY CONSIDERATIONS FOR THIS LAYER
List all security protections implemented in this session.
Be explicit. Include:
- How file uploads are validated
- How file storage is protected
- How user ownership is enforced
- What sensitive data is protected and how
- Any DO NOT rules from the briefing that are especially
  relevant to this layer and how they were enforced
- Any potential risks that still exist

THE EXACT NEXT STEP
Write one clear sentence describing the very first thing the
next session should do. Be specific enough that Claude Code
can start without any additional context.

ANYTHING ELSE THE NEXT SESSION NEEDS TO KNOW
Any context, warnings, or notes that would help the next session
avoid problems or make better decisions.