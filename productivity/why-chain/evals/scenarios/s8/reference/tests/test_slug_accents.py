from blog.slug import slugify


def test_transliterates_accents():
    assert slugify("Café Crème") == "cafe-creme"
    assert slugify("Ångström Über naïve") == "angstrom-uber-naive"


def test_non_latin_still_falls_back():
    assert slugify("日本語") == "untitled"
