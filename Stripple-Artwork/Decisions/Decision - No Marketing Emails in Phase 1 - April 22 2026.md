Decision: What types of emails the app sends
Date: April 22 2026
Status: Final for Phase 1

What we chose
The app only ever sends two types of emails in Phase 1.
Email verification when a new account is created.
Password reset links when a user requests one.
Nothing else.

What this means in plain English
There are no welcome emails, no newsletters, no usage tips,
no promotional messages, and no notifications of any kind
in Phase 1. Every email the app sends is a direct response
to something the user just did and contains only what they
need to complete that action.

Why we chose this
Keeping email to the absolute minimum in Phase 1 has several
benefits. It keeps the SendGrid setup simple. It keeps the
codebase smaller and easier to maintain. It avoids any legal
requirements around marketing email such as unsubscribe links
and consent tracking. And it means every email a user receives
from the app is something they asked for and genuinely need.

When to revisit
When there is a specific business reason to add notifications
or marketing communication. At that point a proper email
preference system and unsubscribe mechanism would need to be
built alongside any new email type. This is a Phase 2 or later
decision.