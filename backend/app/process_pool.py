import asyncio
from concurrent.futures import ProcessPoolExecutor

_process_pool: ProcessPoolExecutor | None = None
# Semaphore value matches max_workers — one permit per worker slot.
# Acquiring before run_in_executor guarantees a slot is free; releasing after
# completion keeps the count accurate. Failing to acquire returns 503 immediately
# without submitting any work to the pool.
_preview_semaphore: asyncio.Semaphore | None = None


def get_process_pool() -> ProcessPoolExecutor:
    if _process_pool is None:
        raise RuntimeError("Process pool accessed before application startup")
    return _process_pool


def get_preview_semaphore() -> asyncio.Semaphore:
    if _preview_semaphore is None:
        raise RuntimeError("Preview semaphore accessed before application startup")
    return _preview_semaphore


def init_process_pool(max_workers: int = 4) -> ProcessPoolExecutor:
    global _process_pool, _preview_semaphore
    _process_pool = ProcessPoolExecutor(max_workers=max_workers)
    _preview_semaphore = asyncio.Semaphore(max_workers)
    return _process_pool


def shutdown_process_pool() -> None:
    global _process_pool, _preview_semaphore
    if _process_pool is not None:
        _process_pool.shutdown(wait=True)
        _process_pool = None
    _preview_semaphore = None
