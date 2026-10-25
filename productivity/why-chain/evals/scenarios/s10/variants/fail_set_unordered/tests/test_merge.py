from newsletter.merge import merge_subscribers
from newsletter.worker import run_import


def test_merge_keeps_order_and_dedupes():
    got = merge_subscribers(["a@x.com", "B@x.com"], [" b@x.com", "c@x.com", "bad"])
    assert got == ["a@x.com", "b@x.com", "c@x.com"]


def test_run_import_small():
    assert run_import(["a@x.com"], ["a@x.com", "d@y.org"]) == ["a@x.com", "d@y.org"]
