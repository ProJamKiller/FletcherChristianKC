#!/usr/bin/env python3
import json
import re
import html
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

SITE_URL = "https://fletcherchristiankc.rip"
SITE_ICON = "https://bafybeihqeeb3l7wuz6gfzfd4hhs2exdm2qob72rbxgqeg2renwmyznzshe.ipfs.dweb.link?filename=allseeingeye.JPG"
DEFAULT_OG_IMAGE = SITE_ICON

AUTHOR_NAME = "Fletcher Christian"
AUTHOR_DISPLAY = "Fletcher Christian KC"
AUTHOR_EMAIL = "fletcher@jamkillerproductions.io"
AUTHOR_IMAGE = "https://bafybeicpqitisgw7mo4r7msku32dc4hkzwlofk25hxk7ygo6j7ctkk7nqa.ipfs.dweb.link?filename=biopic.JPG"

AUTHOR_CREDENTIALS = [
    "Bachelor’s in Communications from University of Arizona Global Campus",
    "Master’s in Theological Studies from Liberty University",
]

AUTHOR_LINKS = [
    ("Jam Killer Productions", "https://jamkillerproductions.io"),
    ("The Mutiny Report", "https://mutinyreport.com"),
    ("JETTAI", "https://jettai.pro"),
]

AUTHOR_BIO_PARAGRAPHS = [
    "Fletcher Christian is a writer, producer, musician, and activist whose work is shaped by lived experience, creative discipline, and a relentless pursuit of truth. A combat veteran of the U.S. Army, Fletcher served nine years and deployed to Afghanistan with the 45th Infantry Brigade, 120th Engineer Battalion in Kandahar. His military service profoundly shaped his understanding of leadership, conflict, survival, and the human cost of war.",
    "After returning home, Fletcher turned toward scholarship and self-examination, earning a Bachelor’s degree in Communications and a Master’s degree in Theological Studies. His academic work deepened a lifelong engagement with questions of faith, meaning, power, and human consciousness. Though his beliefs have evolved over time, his commitment to intellectual honesty and spiritual inquiry remains central to his voice and work.",
    "Music has been a constant throughout that journey. With more than two decades of experience as a musician and creative, Fletcher has used songwriting and production not only as an artistic craft, but as a way of processing life, struggle, and transformation. In 2022, he founded Jam Killer Productions, an independent creative platform through which he has produced multiple albums and expanded his work as both an artist and producer.",
    "In recent years, Fletcher has become an increasingly outspoken voice in political and theological commentary. In early 2026, he launched The Mutiny Report, a platform dedicated to confronting propaganda, religious nationalism, political hypocrisy, and the cultural machinery that drives division and war. His work is especially focused on challenging modern Christian nationalism and exposing the ways theology can be manipulated in service of power, violence, and empire.",
    "At the core of everything Fletcher creates is a hard-earned perspective forged through combat, scholarship, creativity, and personal reinvention. He brings together the instincts of a soldier, the mind of a theologian, and the soul of an artist, using each to speak plainly about war, faith, culture, and what it means to stay human in a world that often rewards the opposite.",
]

ROOT = Path(__file__).resolve().parent
TEMPLATES = ROOT / "templates"
POSTS_JSON = ROOT / "posts.json"
OUTPUT_POSTS_DIR = ROOT / "posts"

INDEX_TEMPLATE = TEMPLATES / "index_template.html"
ARCHIVE_TEMPLATE = TEMPLATES / "archive_template.html"
POST_TEMPLATE = TEMPLATES / "post_template.html"
ABOUT_TEMPLATE = TEMPLATES / "about_template.html"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def slugify(value: str) -> str:
    value = (value or "post").strip().lower()
    value = re.sub(r"[\"'’“”]", "", value)
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-{2,}", "-", value)
    return value.strip("-") or "post"


def format_date(date_string: str) -> str:
    try:
        return datetime.strptime(date_string, "%Y-%m-%d").strftime("%B %-d, %Y")
    except ValueError:
        try:
            return datetime.strptime(date_string, "%Y-%m-%d").strftime("%B %#d, %Y")
        except ValueError:
            return date_string


def strip_html(value: str) -> str:
    value = re.sub(r"<br\s*/?>", " ", value, flags=re.I)
    value = re.sub(r"</p\s*>", "\n\n", value, flags=re.I)
    value = re.sub(r"<[^>]+>", "", value)
    value = html.unescape(value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def json_attr(value: str) -> str:
    return json.dumps(value or "", ensure_ascii=False)[1:-1]


def load_posts() -> list[dict]:
    posts = json.loads(read_text(POSTS_JSON))
    if not isinstance(posts, list):
        raise ValueError("posts.json must contain a top-level array.")

    for post in posts:
        post["slug"] = post.get("slug") or slugify(post.get("title", "post"))
        post["permalink"] = f"{SITE_URL}/posts/{quote(post['slug'])}.html"
        post["formatted_date"] = format_date(post.get("date", ""))
        post["search_text"] = " ".join([
            post.get("title", ""),
            post.get("author", ""),
            post.get("excerpt", ""),
            strip_html(post.get("content", "")),
            " ".join(post.get("tags", [])),
        ]).lower()
        post["image_for_meta"] = post.get("mediaUrl") if post.get("mediaType") == "image" and post.get("mediaUrl") else DEFAULT_OG_IMAGE

    posts.sort(key=lambda p: p.get("date", ""), reverse=True)
    return posts


def meta_line(parts: list[str]) -> str:
    cleaned = [p for p in parts if p]
    out = []
    for i, part in enumerate(cleaned):
        if i:
            out.append('<span class="dot" aria-hidden="true"></span>')
        out.append(part)
    return "".join(out)


def render_tag_spans(tags: list[str]) -> str:
    if not tags:
        return ""
    return '<div class="tag-row">' + "".join(
        f'<span class="tag">{html.escape(tag)}</span>'
        for tag in tags
    ) + "</div>"


def render_filter_tags_attr(tags: list[str]) -> str:
    return html.escape("|".join(tags or []))


def media_markup(post: dict, linked: bool = False, relative_prefix: str = "") -> str:
    media_type = post.get("mediaType")
    media_url = post.get("mediaUrl")
    title = html.escape(post.get("title", "Post image"))
    href = f'{relative_prefix}posts/{quote(post["slug"])}.html'

    if not media_type or not media_url:
        return ""

    if media_type == "image":
        img = f'<img src="{html.escape(media_url)}" alt="{title}" loading="lazy" />'
        if linked:
            img = f'<a href="{href}" aria-label="Read {title}">{img}</a>'
        return f'<div class="post-media">{img}</div>'

    if media_type == "video":
        return f'''
        <div class="post-media">
          <video controls preload="metadata">
            <source src="{html.escape(media_url)}" />
          </video>
        </div>
        '''

    return ""


def featured_post_markup(post: dict) -> str:
    meta_parts = []
    if post.get("author"):
        meta_parts.append(f"<span>{html.escape(post['author'])}</span>")
    if post.get("date"):
        meta_parts.append(f'<time datetime="{html.escape(post["date"])}">{html.escape(post["formatted_date"])}</time>')
    if post.get("tags"):
        meta_parts.append(f"<span>{html.escape(', '.join(post['tags']))}</span>")

    excerpt = f'<p class="post-excerpt">{html.escape(post["excerpt"])}</p>' if post.get("excerpt") else ""
    media = media_markup(post, linked=True)
    tags = render_tag_spans(post.get("tags", []))
    body = f'<div class="post-body">{post.get("content", "")}</div>' if post.get("content") else ""

    return f'''
      <article class="post-card featured-post">
        <div class="post-meta">
          {meta_line(meta_parts)}
        </div>
        <h2 class="featured-title">
          <a href="posts/{quote(post["slug"])}.html">{html.escape(post.get("title", "Untitled"))}</a>
        </h2>
        {excerpt}
        {media}
        {tags}
        {body}
        <div class="post-actions">
          <button class="share-button" type="button" data-share-url="{html.escape(post["permalink"])}" data-share-title="{html.escape(post.get("title", "Post"))}" data-share-text="{html.escape(post.get("excerpt", ""))}">Share</button>
          <a class="share-button" href="posts/{quote(post["slug"])}.html">Open Post</a>
        </div>
      </article>
    '''


def recent_preview_markup(post: dict) -> str:
    meta_parts = []
    if post.get("author"):
        meta_parts.append(f"<span>{html.escape(post['author'])}</span>")
    if post.get("date"):
        meta_parts.append(f'<time datetime="{html.escape(post["date"])}">{html.escape(post["formatted_date"])}</time>')

    excerpt = f'<p class="post-excerpt">{html.escape(post["excerpt"])}</p>' if post.get("excerpt") else ""
    media = media_markup(post, linked=True)
    tags = render_tag_spans(post.get("tags", []))

    return f'''
      <article class="preview-card" data-filter-card data-search="{html.escape(post["search_text"])}" data-tags="{render_filter_tags_attr(post.get("tags", []))}">
        <div class="preview-grid">
          <div class="preview-copy">
            <div class="post-meta">
              {meta_line(meta_parts)}
            </div>
            <h3 class="post-title">
              <a href="posts/{quote(post["slug"])}.html">{html.escape(post.get("title", "Untitled"))}</a>
            </h3>
            {excerpt}
            {tags}
            <div class="post-actions">
              <a class="share-button" href="posts/{quote(post["slug"])}.html">Read Post</a>
            </div>
          </div>
          <div class="preview-media">
            {media}
          </div>
        </div>
      </article>
    '''


def archive_preview_markup(post: dict) -> str:
    meta_parts = []
    if post.get("author"):
        meta_parts.append(f"<span>{html.escape(post['author'])}</span>")
    if post.get("date"):
        meta_parts.append(f'<time datetime="{html.escape(post["date"])}">{html.escape(post["formatted_date"])}</time>')
    if post.get("tags"):
        meta_parts.append(f"<span>{html.escape(', '.join(post['tags']))}</span>")

    excerpt = f'<p class="archive-excerpt">{html.escape(post["excerpt"])}</p>' if post.get("excerpt") else ""
    media = media_markup(post, linked=True)
    tags = render_tag_spans(post.get("tags", []))

    return f'''
      <article class="archive-item" id="{html.escape(post["slug"])}" data-filter-card data-search="{html.escape(post["search_text"])}" data-tags="{render_filter_tags_attr(post.get("tags", []))}">
        <div class="archive-meta">
          {meta_line(meta_parts)}
        </div>
        <h2><a href="posts/{quote(post["slug"])}.html">{html.escape(post.get("title", "Untitled"))}</a></h2>
        {excerpt}
        {media}
        {tags}
        <div class="post-actions">
          <a class="share-button" href="posts/{quote(post["slug"])}.html">Read Post</a>
          <button class="share-button" type="button" data-share-url="{html.escape(post["permalink"])}" data-share-title="{html.escape(post.get("title", "Post"))}" data-share-text="{html.escape(post.get("excerpt", ""))}">Share</button>
        </div>
      </article>
    '''


def render_index(posts: list[dict]) -> str:
    if not posts:
        raise ValueError("posts.json does not contain any posts.")

    template = read_text(INDEX_TEMPLATE)
    featured = posts[0]
    recent = posts[1:]

    recent_cards = "\n".join(recent_preview_markup(post) for post in recent) if recent else '<div class="empty">No additional posts yet.</div>'
    recent_count = len(recent)

    replacements = {
        "{{FEATURED_POST}}": featured_post_markup(featured),
        "{{RECENT_POSTS}}": recent_cards,
        "{{RECENT_COUNT_LABEL}}": f"Showing {recent_count} more post{'s' if recent_count != 1 else ''}" if recent else "No additional posts yet",
    }

    for key, value in replacements.items():
        template = template.replace(key, value)

    return template


def render_archive(posts: list[dict]) -> str:
    template = read_text(ARCHIVE_TEMPLATE)
    cards = "\n".join(archive_preview_markup(post) for post in posts) if posts else '<div class="empty">No posts yet.</div>'

    replacements = {
        "{{ARCHIVE_POSTS}}": cards,
        "{{ARCHIVE_COUNT_LABEL}}": f"Showing {len(posts)} post{'s' if len(posts) != 1 else ''}",
    }

    for key, value in replacements.items():
        template = template.replace(key, value)

    return template


def render_post_tags(tags: list[str]) -> str:
    if not tags:
        return ""
    return "\n".join(f'<span class="tag">{html.escape(tag)}</span>' for tag in tags)


def fill_post_template(template: str, post: dict) -> str:
    replacements = {
        "{{POST_TITLE}}": html.escape(post.get("title", "")),
        "{{POST_TITLE_ATTR}}": html.escape(post.get("title", "")),
        "{{POST_TITLE_JSON}}": json_attr(post.get("title", "")),
        "{{POST_EXCERPT}}": html.escape(post.get("excerpt", "")),
        "{{POST_EXCERPT_ATTR}}": html.escape(post.get("excerpt", "")),
        "{{POST_EXCERPT_JSON}}": json_attr(post.get("excerpt", "")),
        "{{POST_AUTHOR}}": html.escape(post.get("author", "")),
        "{{POST_AUTHOR_JSON}}": json_attr(post.get("author", "")),
        "{{POST_DATE}}": html.escape(post.get("date", "")),
        "{{POST_DATE_DISPLAY}}": html.escape(post.get("formatted_date", "")),
        "{{POST_URL}}": html.escape(post.get("permalink", "")),
        "{{POST_IMAGE}}": html.escape(post.get("image_for_meta", DEFAULT_OG_IMAGE)),
        "{{POST_CONTENT}}": post.get("content", ""),
        "{{POST_TAGS}}": render_post_tags(post.get("tags", [])),
    }

    for key, value in replacements.items():
        template = template.replace(key, value)

    return template


def render_single_post(post: dict) -> str:
    template = read_text(POST_TEMPLATE)
    return fill_post_template(template, post)


def render_about_credentials() -> str:
    return "".join(
        f"<li>{html.escape(item)}</li>"
        for item in AUTHOR_CREDENTIALS
    )


def render_about_links() -> str:
    return "".join(
        f'<a class="button" href="{html.escape(url)}" target="_blank" rel="noopener">{html.escape(label)}</a>'
        for label, url in AUTHOR_LINKS
    )


def render_about_bio() -> str:
    return "\n".join(
        f"<p>{html.escape(paragraph)}</p>"
        for paragraph in AUTHOR_BIO_PARAGRAPHS
    )


def render_about() -> str:
    template = read_text(ABOUT_TEMPLATE)

    replacements = {
        "{{AUTHOR_NAME}}": html.escape(AUTHOR_NAME),
        "{{AUTHOR_DISPLAY}}": html.escape(AUTHOR_DISPLAY),
        "{{AUTHOR_EMAIL}}": html.escape(AUTHOR_EMAIL),
        "{{AUTHOR_IMAGE}}": html.escape(AUTHOR_IMAGE),
        "{{AUTHOR_CREDENTIALS}}": render_about_credentials(),
        "{{AUTHOR_LINKS}}": render_about_links(),
        "{{AUTHOR_BIO}}": render_about_bio(),
        "{{AUTHOR_IMAGE_ALT}}": html.escape(f"{AUTHOR_NAME} portrait"),
    }

    for key, value in replacements.items():
        template = template.replace(key, value)

    return template


def main() -> None:
    posts = load_posts()

    required_templates = [
        INDEX_TEMPLATE,
        ARCHIVE_TEMPLATE,
        POST_TEMPLATE,
        ABOUT_TEMPLATE,
    ]

    for template_path in required_templates:
        if not template_path.exists():
            raise FileNotFoundError(f"Missing template: {template_path}")

    write_text(ROOT / "index.html", render_index(posts))
    write_text(ROOT / "archive.html", render_archive(posts))
    write_text(ROOT / "about.html", render_about())

    OUTPUT_POSTS_DIR.mkdir(parents=True, exist_ok=True)
    for post in posts:
        write_text(OUTPUT_POSTS_DIR / f"{post['slug']}.html", render_single_post(post))

    print(f"Built {len(posts)} post pages.")
    print("Generated:")
    print(f"  {ROOT / 'index.html'}")
    print(f"  {ROOT / 'archive.html'}")
    print(f"  {ROOT / 'about.html'}")
    print(f"  {OUTPUT_POSTS_DIR}/")


if __name__ == "__main__":
    main()