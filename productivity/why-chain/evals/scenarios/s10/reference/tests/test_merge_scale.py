import time

from newsletter.merge import merge_subscribers


def test_large_merge_is_fast():
    existing = [f"user{i}@example.com" for i in range(50_000)]
    incoming = [f"USER{i}@example.com " for i in range(40_000, 70_000)]
    start = time.perf_counter()
    got = merge_subscribers(existing, incoming)
    assert time.perf_counter() - start < 2
    assert len(got) == 70_000 and got[0] == "user0@example.com" and got[-1] == "user69999@example.com"
