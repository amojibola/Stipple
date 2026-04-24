Decision: How image previews are generated when users adjust sliders
Date: April 22 2026
Status: Final for Phase 1 - revisit if concurrent users cause slowdowns

What we chose
Previews run directly inside the main API server using a dedicated
pool of 4 separate processes reserved exclusively for image work.
Previews are not sent to the background job queue.

What this means in plain English
When a user moves a slider the app waits 300 milliseconds to see if
they move it again. If they stop, the current settings are sent to
the server. The server shrinks the image to 400 pixels wide and runs
the stipple process on that small version. The result comes back in
under 2 seconds in most cases.

The image processing runs in its own isolated pool of processes that
are completely separate from the processes handling everything else.
This means that even if something goes wrong during preview generation
it cannot affect other users or other parts of the app.

Results are also cached. If a user moves a slider, previews the
result, moves it back, and previews again - the second preview for
the original position comes back instantly from the cache rather than
being processed again. The cache stores results for one hour.

Why we chose this over using the background job queue
The background queue (Celery) adds at least half a second of overhead
just to receive and start a job before any actual work begins. For a
preview on a 400 pixel wide image that processes in about 50
milliseconds, queuing it would make the total wait time longer not
shorter. Direct processing is faster and simpler for this use case.

Why separate processes instead of separate threads
Python has a limitation called the Global Interpreter Lock that
prevents true parallel processing using threads for CPU-heavy work
like image processing. Separate processes do not have this limitation.
Using separate processes also means a crash in the image processing
code is completely contained and cannot affect the rest of the app.

When to revisit this decision
If the app reaches a point where many users are adjusting sliders
simultaneously and previews start feeling slow, the solution is to
move previews to a short queue with fast polling. This change can
be made without altering the database schema or any other part of
the architecture.