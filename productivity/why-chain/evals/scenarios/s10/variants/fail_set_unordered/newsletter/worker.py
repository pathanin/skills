import concurrent.futures

from .merge import merge_subscribers

JOB_TIMEOUT_SECONDS = 5


class ImportTimeout(Exception):
    pass


def run_import(existing, incoming, timeout=None):
    timeout = JOB_TIMEOUT_SECONDS if timeout is None else timeout
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = pool.submit(merge_subscribers, existing, incoming)
    try:
        return future.result(timeout=timeout)
    except concurrent.futures.TimeoutError:
        raise ImportTimeout(f"import exceeded {timeout}s") from None
    finally:
        pool.shutdown(wait=False)
