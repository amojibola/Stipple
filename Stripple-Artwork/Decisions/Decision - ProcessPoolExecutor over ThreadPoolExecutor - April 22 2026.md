Decision: Which type of parallel processing to use for image work
Date: April 22 2026
Status: Final

What we chose
ProcessPoolExecutor - a pool of 4 completely separate processes
reserved exclusively for image processing work.

What this means in plain English
When the app needs to process an image for a preview it uses one
of four reserved slots. Each slot is a completely independent
process running separately from the main app. If something goes
wrong in one slot it is completely contained and cannot affect
anything else. Up to 4 previews can be processed at the same
time without slowing down any other part of the app.

Why not threads
Python has a built-in limitation called the Global Interpreter
Lock. In simple terms this means Python can only truly do one
CPU-heavy task at a time even if multiple threads are set up.
For work like image processing that uses a lot of computing
power, threads do not actually run in parallel - they take turns.
Separate processes do not have this limitation and can genuinely
run at the same time.

There is also a safety benefit. A crash inside a thread can
potentially bring down the entire app. A crash inside a separate
process is completely contained and the main app keeps running
normally.

What this means practically
Login requests, project saves, and all other actions continue
working normally even while images are being processed. The
image processing work is completely isolated from everything else.