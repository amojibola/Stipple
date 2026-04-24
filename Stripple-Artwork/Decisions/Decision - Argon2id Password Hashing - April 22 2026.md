Decision: How user passwords are stored securely
Date: April 22 2026
Status: Final - do not change parameters without security review

What we chose
Argon2id with these specific settings:
  time_cost = 2
  memory_cost = 65536
  parallelism = 2

What this means in plain English
Passwords are never stored anywhere in the app. Not in the database,
not in logs, not anywhere. Instead, when a user sets a password it
is run through a one-way scrambling process called hashing. What gets
stored looks like random gibberish. When the user logs in later, their
entered password is scrambled the same way and the two scrambled
versions are compared. If they match, the password was correct.

The scrambling is deliberately slow and memory-intensive. This means
that even if someone stole the database, trying to reverse engineer
the original passwords would take an impractical amount of time and
computing power.

Why we chose Argon2id specifically
Argon2id won an international competition called the Password Hashing
Competition specifically designed to find the best algorithm for this
purpose. It is superior to the older bcrypt algorithm that many apps
still use because it is much harder to attack using graphics cards,
which attackers commonly use to speed up password cracking attempts.

The specific settings chosen (time_cost=2, memory_cost=65536,
parallelism=2) are calibrated to be slow enough to resist attacks
while still being fast enough that legitimate users do not notice
any delay when logging in.

What this means for the app owner
There is no way to recover or look up a user's password. If a user
forgets their password the only option is the password reset flow
which emails them a one-time link. This is intentional and correct.