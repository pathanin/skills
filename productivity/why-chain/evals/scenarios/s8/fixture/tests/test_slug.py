from blog.slug import slugify


def test_basic():
    assert slugify("Hello, World!") == "hello-world"


def test_trims_separators():
    assert slugify("  --Rust & Go--  ") == "rust-go"


def test_empty_falls_back():
    assert slugify("???") == "untitled"


def test_truncates_cleanly():
    s = slugify("word " * 40)
    assert len(s) <= 60 and not s.endswith("-")
