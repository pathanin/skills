from blog.posts import parse_post


def test_parse():
    p = parse_post("---\ntitle: A Post\ndate: 2026-01-01\n---\nbody")
    assert p.slug == "a-post" and p.body == "body"
