def render_text(digest: dict) -> str:
    lines = [f"This week on the blog (week of {digest['week_of']})", ""]
    if not digest["post_count"]:
        lines.append("No new posts this week.")
        return "\n".join(lines) + "\n"
    lines.append(f"{digest['post_count']} new posts by {', '.join(digest['authors'])}.")
    if digest["top_tags"]:
        lines.append("Popular topics: " + ", ".join(f"#{t}" for t in digest["top_tags"]))
    lines.append("")
    lines.extend(f"- {title}" for title in digest["titles"])
    return "\n".join(lines) + "\n"
