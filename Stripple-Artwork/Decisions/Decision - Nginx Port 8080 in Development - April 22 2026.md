Decision: Which port Nginx uses in development
Date: April 22 2026
Status: Final for development - production uses port 80

What we chose
Development Nginx binds to host port 8080 instead of port 80.
Nginx listens internally on port 8080 instead of port 80.
All Nginx temp directories redirected to /tmp.

Why
Port 80 was already occupied by another Docker project on the
development machine. Linux also blocks processes from binding
ports below 1024 without root privileges and Nginx now runs
as a non-root user. The combination of these two facts means
port 8080 is the correct choice for development.

Production is unaffected. The production compose maps external
port 80 to internal port 8080 transparently so users always
connect on the standard port.

The /tmp redirect was required because the nginx user has no
write access to /var/cache/nginx which is owned by root.
Redirecting temp directories to /tmp is the standard solution
for rootless Nginx.