Decision: How to handle AI audit findings that seem overly strict
Date: April 23 2026
Status: Standing guidance for all future audit rounds

What happened
During the Layer 2 audit Codex flagged the raw token existing
as a function parameter inside the email building service as a
security violation. The requirement was that raw tokens must
never be written to logs, files, or external stores. Codex
interpreted this to mean tokens cannot exist anywhere in the
codebase including as in-memory variables inside functions
that need them to do their job.

This was an incorrect interpretation. The email service must
have access to the raw token to put it in the verification
email. That is the entire purpose of the function.

The rule that applies going forward
When Codex flags something ask this question before sending
it to Claude Code for fixes:

Is this code writing the sensitive value to somewhere it
should not be, or is it just using the value to do its job?

Using a token to build an email = doing its job. Correct.
Writing a token to a log = writing it where it should not be.

These are very different things and the distinction matters.

When to push back on an audit finding
Push back when the flagged code is doing exactly what it is
supposed to do and removing or changing it would break the
feature. Always verify with Claude Code before dismissing
a finding. Claude Code confirmed all four security checks
were true in this case before the finding was dismissed.

When to always act on an audit finding
Always act on findings involving logs, files, external stores,
database writes, API responses, or cookie attributes. These
are the places where sensitive values should never appear
and audit findings in these areas are almost always correct.