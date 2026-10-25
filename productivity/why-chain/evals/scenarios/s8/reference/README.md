# blog

Tiny static blog builder. Posts live in `posts/*.md` with a front-matter
block; each post is written to `site/<slug>/index.html`.

    python -m blog.build posts site

Slugs come from post titles via `blog.slug.slugify`. No third-party
dependencies; keep it that way.
