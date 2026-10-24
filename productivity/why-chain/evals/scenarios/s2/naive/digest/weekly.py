from datetime import date, datetime, time, timedelta

from digest.posts import Post

TOP_TAG_COUNT = 3


def week_bounds(week_start: date) -> tuple[datetime, datetime]:
    start = datetime.combine(week_start, time.min)
    return start, start + timedelta(days=7)


def posts_in_week(posts: list[Post], week_start: date) -> list[Post]:
    start, end = week_bounds(week_start)
    return sorted(
        (p for p in posts if start <= p.published_at.replace(tzinfo=None) < end),
        key=lambda p: p.published_at,
    )


def top_tags(posts: list[Post], limit: int = TOP_TAG_COUNT) -> list[str]:
    """Most used tags, ranked by how many posts carry them."""
    tags = {tag for post in posts for tag in post.tag_keys}
    counts = {tag: sum(1 for post in posts if tag in post.tag_keys) for tag in tags}
    return sorted(counts, key=counts.get, reverse=True)[:limit]


def build_digest(posts: list[Post], week_start: date) -> dict:
    week = posts_in_week(posts, week_start)
    return {
        "week_of": week_start.isoformat(),
        "post_count": len(week),
        "authors": sorted({p.author for p in week}),
        "top_tags": top_tags(week),
        "titles": [p.title for p in week],
    }
