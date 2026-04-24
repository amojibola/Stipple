Decision: How the app sends emails to users
Date: April 22 2026
Status: Final

What we chose
SendGrid free tier using their SMTP service. Used exclusively for
two things: email verification on signup and password reset links.

What this means in plain English
When a user creates an account or requests a password reset, the app
needs to send them an email. Rather than trying to send that email
directly from our server, we use SendGrid as a middleman. SendGrid
specialises in sending email reliably and their service is trusted
by Gmail, Outlook, and every other major email provider.

Why we chose this
If the app tried to send emails directly from the Hostinger server,
those emails would land in spam the majority of the time. This is
because email providers automatically distrust emails coming from
unknown server IP addresses. SendGrid has spent years building a
trusted reputation with every major email provider. Using them means
verification emails arrive in the inbox instead of the spam folder.

The free tier allows 100 emails per day. At that rate the app could
onboard roughly 50 new users per day before needing to upgrade. More
than sufficient for launch and early growth.

What is needed to use it
A SendGrid account with a verified sender address or domain.
An API key stored in the .env file as SMTP_PASSWORD.
The value of SMTP_USER is literally the word apikey - that is not
a placeholder, it is what SendGrid requires.

What we are not using it for
No marketing emails, newsletters, or notifications in Phase 1.
Strictly transactional emails only.