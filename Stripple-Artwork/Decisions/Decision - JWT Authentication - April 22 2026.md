Decision: How user login sessions work
Date: April 22 2026
Status: Final - do not change without strong reason

What we chose
JWT RS256 access tokens lasting 15 minutes combined with refresh tokens
lasting 7 days. Both stored as secure cookies that JavaScript cannot
read. Refresh tokens are stored as a scrambled fingerprint in Redis.

What this means in plain English
When a user logs in they get two invisible tokens stored in their
browser. One lasts 15 minutes and is used to prove who they are on
every request. When it expires the other token (which lasts 7 days)
is used to silently get a new one without making the user log in again.
When a user logs out the 7 day token is immediately deleted from the
server, making both tokens useless instantly.

Why we chose this
Three options were considered:

Option 1 - Sessions only
Simple but requires the server to remember every logged in user.
Does not work well if the app ever runs on more than one server.
Logging out works instantly but scaling is harder.

Option 2 - JWT tokens only
The server does not need to remember anything. Fast and scalable.
But there is no way to force a logout - a stolen token stays valid
until it naturally expires.

Option 3 - JWT plus refresh tokens (what we chose)
Gets the best of both. The short lived access token means a stolen
token expires quickly. The refresh token stored on the server means
logout actually works - the token is deleted and immediately invalid.
This is the right choice for an app that handles user accounts and
private files.

What we rejected and why
Simple session-based auth was suggested as a simpler alternative.
Rejected because it has the same Redis dependency as this approach
but with worse logout and scaling options. The added complexity of
the hybrid approach is justified by the security benefits.