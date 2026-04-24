Decision: How to handle repeated failed login attempts
Date: April 22 2026
Status: Final

What we chose
Increasing time delays targeting the attacking IP address only.
No account lockout of any kind.

What this means in plain English
If someone repeatedly enters the wrong password the app makes
them wait longer and longer between each attempt. After the
third wrong try the delays begin. One second, then two, then
five, then ten, then thirty, then sixty seconds. After twenty
failed attempts from the same network address that address is
blocked for one hour. The account being targeted is never
locked or suspended at any point.

Why not lock the account after too many failures
Account lockout sounds like a security feature but it creates
a serious problem. If accounts lock after failed attempts an
attacker can deliberately lock any account they know the email
address for by simply entering wrong passwords repeatedly. This
is called a denial of service attack and it requires no password
knowledge at all. The attacker does not get into the account
but they prevent the real owner from getting in either.

By targeting the IP address of the attacker rather than the
account being attacked the real user can still log in from
their own device while the attacker is blocked.

What gets logged
Every failed login attempt is recorded in the audit log with
the IP address and timestamp. Email addresses and passwords
are never logged under any circumstances. If a pattern of
suspicious activity appears against a specific account it can
be reviewed manually by the app owner.