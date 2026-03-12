#!/usr/bin/env python3
import json
import re
import html
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

SITE_URL = "https://fletcherchristiankc.rip"

ROOT = Path(__file__).resolve().parent
TEMPLATES = ROOT / "templates"
POSTS_JSON = ROOT / "posts.json"
OUTPUT_POSTS_DIR = ROOT / "posts"

INDEX_TEMPLATE = TEMPLATES / "index_template.html"
ARCHIVE_TEMPLATE = TEMPLATES / "archive_template.html"
POST_TEMPLATE = TEMPLATES / "post_template.html"


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


def load_posts() -> list[dict]:
    posts = json.loads(read_text(POSTS_JSON))
    if not isinstance(posts, list):
        raise ValueError("posts.json must contain a top-level array.")

    for post in posts:
        post["slug"] = post.get("slug") or slugify(post.get("title", "post"))
        post["permalink"] = f"{SITE_URL}/posts/{post['slug']}.html"
        post["formatted_date"] = format_date(post.get("date", ""))
        post["search_text"] = " ".join([
            post.get("title", ""),
            post.get("author", ""),
            post.get("excerpt", ""),
            strip_html(post.get("content", "")),
            " ".join(post.get("tags", [])),
        ]).lower()

    posts.sort(key=lambda p: p.get("date", ""), reverse=True)
    return posts


def remove_old_scripts(template_html: str) -> str:
    html_out = re.sub(r'\s*<script src="posts\.js"></script>\s*', "\n", template_html, flags=re.I)
    html_out = re.sub(
        r'\s*<script>\s*\(\(\)\s*=>\s*\{[\s\S]*?</script>\s*</body>\s*</html>\s*$',
        "\n</body>\n</html>\n",
        html_out,
        flags=re.I
    )
    return html_out


def media_markup(post: dict) -> str:
    media_type = post.get("mediaType")
    media_url = post.get("mediaUrl")
    title = html.escape(post.get("title", "Post image"))

    if not media_type or not media_url:
        return ""

    if media_type == "image":
        return f'''
            <div class="post-media">
              <img src="{html.escape(media_url)}" alt="{title}" loading="lazy" />
            </div>
        '''

    if media_type == "video":
        return f'''
            <div class="post-media">
              <video controls preload="metadata">
                <source src="{html.escape(media_url)}" />
              </video>
            </div>
        '''

    return ""


def meta_line(parts: list[str]) -> str:
    cleaned = [p for p in parts if p]
    out = []
    for i, part in enumerate(cleaned):
        if i:
            out.append('<span class="dot" aria-hidden="true"></span>')
        out.append(part)
    return "".join(out)


def tags_buttons(tags: list[str]) -> str:
    if not tags:
        return ""
    return '<div class="tag-row">' + "".join(
        f'<button class="tag" type="button" data-tag="{html.escape(tag)}">{html.escape(tag)}</button>'
        for tag in tags
    ) + "</div>"


def index_card(post: dict) -> str:
    meta_parts = []
    if post.get("author"):
        meta_parts.append(f"<span>{html.escape(post['author'])}</span>")
    if post.get("date"):
        meta_parts.append(f'<time datetime="{html.escape(post["date"])}">{html.escape(post["formatted_date"])}</time>')
    if post.get("tags"):
        meta_parts.append(f"<span>{html.escape(', '.join(post['tags']))}</span>")

    excerpt = f'<p class="post-excerpt">{html.escape(post["excerpt"])}</p>' if post.get("excerpt") else ""
    media = media_markup(post)
    tags = tags_buttons(post.get("tags", []))
    body = f'<div class="post-body">{post.get("content", "")}</div>' if post.get("content") else ""

    return f'''
      <article class="post-card" id="{html.escape(post["slug"])}" data-post-card data-search="{html.escape(post["search_text"])}" data-tags="{html.escape("|".join(post.get("tags", [])))}">
        <div class="post-meta">
          {meta_line(meta_parts)}
        </div>
        <h3 class="post-title"><a href="posts/{quote(post["slug"])}.html">{html.escape(post.get("title", "Untitled"))}</a></h3>
        {excerpt}
        {media}
        {tags}
        {body}
        <div class="post-actions">
          <button class="share-button" type="button" data-share-url="{html.escape(post["permalink"])}" data-share-title="{html.escape(post.get("title", "Post"))}" data-share-text="{html.escape(post.get("excerpt", ""))}">Share</button>
        </div>
      </article>
    '''


def archive_card(post: dict) -> str:
    meta_parts = []
    if post.get("author"):
        meta_parts.append(f"<span>{html.escape(post['author'])}</span>")
    if post.get("date"):
        meta_parts.append(f'<time datetime="{html.escape(post["date"])}">{html.escape(post["formatted_date"])}</time>')
    if post.get("tags"):
        meta_parts.append(f"<span>{html.escape(', '.join(post['tags']))}</span>")

    excerpt = f'<p class="archive-excerpt">{html.escape(post["excerpt"])}</p>' if post.get("excerpt") else ""
    media = media_markup(post)
    tags = tags_buttons(post.get("tags", []))
    body = f'<div class="post-body">{post.get("content", "")}</div>' if post.get("content") else ""

    return f'''
      <article class="archive-item" id="{html.escape(post["slug"])}" data-post-card data-search="{html.escape(post["search_text"])}" data-tags="{html.escape("|".join(post.get("tags", [])))}">
        <div class="archive-meta">
          {meta_line(meta_parts)}
        </div>
        <h2><a href="posts/{quote(post["slug"])}.html">{html.escape(post.get("title", "Untitled"))}</a></h2>
        {excerpt}
        {media}
        {tags}
        {body}
        <div class="post-actions">
          <button class="share-button" type="button" data-share-url="{html.escape(post["permalink"])}" data-share-title="{html.escape(post.get("title", "Post"))}" data-share-text="{html.escape(post.get("excerpt", ""))}">Share</button>
        </div>
      </article>
    '''


def shared_listing_script(mode: str) -> str:
    results_text = (
        "resultsLabel.textContent = visible ? `Showing ${visible} latest post${visible === 1 ? '' : 's'}` : 'No matching posts';"
        if mode == "index"
        else "resultsLabel.textContent = visible ? `Showing ${visible} post${visible === 1 ? '' : 's'}` : 'No matching posts';"
    )

    return f"""
  <script>
    (() => {{
      const searchInput = document.getElementById('searchInput');
      const tagCloud = document.getElementById('tagCloud');
      const resultsLabel = document.getElementById('resultsLabel');
      const year = document.getElementById('year');
      const posts = Array.from(document.querySelectorAll('[data-post-card]'));
      if (year) year.textContent = new Date().getFullYear();

      let activeTag = '';
      let query = '';

      const allTags = [...new Set(
        posts.flatMap(post => (post.dataset.tags || '').split('|').map(tag => tag.trim()).filter(Boolean))
      )].sort((a, b) => a.localeCompare(b));

      const makeButton = (tag, isActive = false) => {{
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'tag' + (isActive ? ' active' : '');
        button.textContent = tag;
        return button;
      }};

      const renderTags = () => {{
        tagCloud.innerHTML = '';
        if (!allTags.length) {{
          tagCloud.innerHTML = '<div class="empty">No tags yet.</div>';
          return;
        }}

        const all = makeButton('All', !activeTag);
        all.addEventListener('click', () => {{
          activeTag = '';
          render();
        }});
        tagCloud.appendChild(all);

        allTags.forEach(tag => {{
          const button = makeButton(tag, activeTag === tag);
          button.addEventListener('click', () => {{
            activeTag = activeTag === tag ? '' : tag;
            render();
          }});
          tagCloud.appendChild(button);
        }});
      }};

      const matches = (post) => {{
        const haystack = (post.dataset.search || '').toLowerCase();
        const tags = (post.dataset.tags || '').split('|').map(t => t.trim()).filter(Boolean);
        const queryMatch = !query || haystack.includes(query);
        const tagMatch = !activeTag || tags.includes(activeTag);
        return queryMatch && tagMatch;
      }};

      const render = () => {{
        let visible = 0;
        posts.forEach(post => {{
          const show = matches(post);
          post.style.display = show ? '' : 'none';
          if (show) visible += 1;
        }});
        {results_text}
        renderTags();

        if (window.location.hash) {{
          const target = document.querySelector(window.location.hash);
          if (target && target.style.display !== 'none') {{
            setTimeout(() => {{
              target.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
            }}, 120);
          }}
        }}
      }};

      if (searchInput) {{
        searchInput.addEventListener('input', (event) => {{
          query = String(event.target.value || '').trim().toLowerCase();
          render();
        }});
      }}

      document.addEventListener('click', async (event) => {{
        const button = event.target.closest('.share-button');
        if (!button) return;

        const url = button.dataset.shareUrl;
        const title = button.dataset.shareTitle || 'Post';
        const text = button.dataset.shareText || '';

        try {{
          if (navigator.share) {{
            await navigator.share({{ title, text, url }});
          }} else {{
            await navigator.clipboard.writeText(url);
            const original = button.textContent;
            button.textContent = 'Link Copied';
            setTimeout(() => {{
              button.textContent = original;
            }}, 1800);
          }}
        }} catch (error) {{
          console.error('Share failed:', error);
        }}
      }});

      render();
    }})();
  </script>
</body>
</html>
"""


def render_index(posts: list[dict]) -> str:
    template = remove_old_scripts(read_text(INDEX_TEMPLATE))
    latest = posts[:6]
    cards = "\n".join(index_card(post) for post in latest)

    template = template.replace(
        '<div class="posts" id="postsContainer"></div>',
        f'<div class="posts" id="postsContainer">\n{cards}\n</div>'
    )

    template = re.sub(
        r'(<div class="section-kicker" id="resultsLabel">).*?(</div>)',
        rf'\1Showing {len(latest)} latest post{"s" if len(latest) != 1 else ""}\2',
        template,
        count=1,
        flags=re.S
    )

    template = template.replace("</body>\n</html>", shared_listing_script("index"))
    return template


def render_archive(posts: list[dict]) -> str:
    template = remove_old_scripts(read_text(ARCHIVE_TEMPLATE))
    cards = "\n".join(archive_card(post) for post in posts)

    template = template.replace(
        '<div id="archiveContainer"></div>',
        f'<div id="archiveContainer">\n{cards}\n</div>'
    )

    template = re.sub(
        r'(<div class="archive-count" id="resultsLabel">).*?(</div>)',
        rf'\1Showing {len(posts)} post{"s" if len(posts) != 1 else ""}\2',
        template,
        count=1,
        flags=re.S
    )

    template = template.replace("</body>\n</html>", shared_listing_script("archive"))
    return template


def render_post_tags(tags: list[str]) -> str:
    if not tags:
        return ""
    return "\n".join(f'<span class="tag">{html.escape(tag)}</span>' for tag in tags)


def fill_post_template(template: str, post: dict) -> str:
    replacements = {
        "{{POST_TITLE}}": html.escape(post.get("title", "")),
        "{{POST_TITLE_ATTR}}": html.escape(post.get("title", "")),
        "{{POST_TITLE_JSON}}": json.dumps(post.get("title", ""), ensure_ascii=False)[1:-1],
        "{{POST_EXCERPT}}": html.escape(post.get("excerpt", "")),
        "{{POST_EXCERPT_ATTR}}": html.escape(post.get("excerpt", "")),
        "{{POST_EXCERPT_JSON}}": json.dumps(post.get("excerpt", ""), ensure_ascii=False)[1:-1],
        "{{POST_AUTHOR}}": html.escape(post.get("author", "")),
        "{{POST_AUTHOR_JSON}}": json.dumps(post.get("author", ""), ensure_ascii=False)[1:-1],
        "{{POST_DATE}}": html.escape(post.get("date", "")),
        "{{POST_DATE_DISPLAY}}": html.escape(post.get("formatted_date", "")),
        "{{POST_URL}}": html.escape(post.get("permalink", "")),
        "{{POST_IMAGE}}": html.escape(post.get("mediaUrl", "")),
        "{{POST_CONTENT}}": post.get("content", ""),
        "{{POST_TAGS}}": render_post_tags(post.get("tags", [])),
    }

    for key, value in replacements.items():
        template = template.replace(key, value)

    return template


def render_single_post(post: dict) -> str:
    template = read_text(POST_TEMPLATE)
    return fill_post_template(template, post)


def main() -> None:
    posts = load_posts()

    if not INDEX_TEMPLATE.exists():
        raise FileNotFoundError("Missing templates/index_template.html")
    if not ARCHIVE_TEMPLATE.exists():
        raise FileNotFoundError("Missing templates/archive_template.html")
    if not POST_TEMPLATE.exists():
        raise FileNotFoundError("Missing templates/post_template.html")

    write_text(ROOT / "index.html", render_index(posts))
    write_text(ROOT / "archive.html", render_archive(posts))

    OUTPUT_POSTS_DIR.mkdir(parents=True, exist_ok=True)
    for post in posts:
        write_text(OUTPUT_POSTS_DIR / f"{post['slug']}.html", render_single_post(post))

    print(f"Built {len(posts)} post pages.")
    print("Generated:")
    print(f"  {ROOT / 'index.html'}")
    print(f"  {ROOT / 'archive.html'}")
    print(f"  {OUTPUT_POSTS_DIR}/")


if __name__ == "__main__":
    main()