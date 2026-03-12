#!/usr/bin/env python3
import json
import re
import html
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

SITE_URL = "https://fletcherchristiankc.rip"
SITE_NAME = "Rants in Person"
AUTHOR_NAME = "Fletcher Christian KC"

ROOT = Path(__file__).resolve().parent
TEMPLATES = ROOT / "templates"
POSTS_JSON = ROOT / "posts.json"
POSTS_DIR = ROOT / "posts"

INDEX_TEMPLATE = TEMPLATES / "index_template.html"
ARCHIVE_TEMPLATE = TEMPLATES / "archive_template.html"
POST_TEMPLATE = TEMPLATES / "post_template.html"

INDEX_POSTS_MARKER = '<div class="posts" id="postsContainer"></div>'
ARCHIVE_POSTS_MARKER = '<div id="archiveContainer"></div>'


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
    if not date_string:
        return ""
    try:
        dt = datetime.strptime(date_string, "%Y-%m-%d")
        try:
            return dt.strftime("%B %-d, %Y")
        except ValueError:
            return dt.strftime("%B %#d, %Y")
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
        raise ValueError("posts.json must contain a top-level JSON array.")
    for post in posts:
        if not isinstance(post, dict):
            raise ValueError("Each post in posts.json must be a JSON object.")
        post["slug"] = post.get("slug") or slugify(post.get("title", "post"))
        post["permalink"] = f"{SITE_URL}/posts/{post['slug']}.html"
        post["formatted_date"] = format_date(post.get("date", ""))
        search_blob = " ".join([
            post.get("title", ""),
            post.get("author", ""),
            post.get("excerpt", ""),
            strip_html(post.get("content", "")),
            " ".join(post.get("tags", []))
        ])
        post["search_text"] = search_blob.lower()
    posts.sort(key=lambda p: p.get("date", ""), reverse=True)
    return posts


def remove_old_runtime(template_html: str) -> str:
    template_html = re.sub(r'\s*<script\s+src="posts\.js"></script>\s*', "\n", template_html, flags=re.I)
    template_html = re.sub(
        r'\s*<script>\s*\(\(\)\s*=>\s*\{[\s\S]*?</script>\s*</body>\s*</html>\s*$',
        "\n</body>\n</html>\n",
        template_html,
        flags=re.I,
    )
    return template_html


def set_meta(template_html: str, *, title: str, description: str, canonical: str,
             og_title: str, og_description: str, og_url: str, og_image: str,
             twitter_title: str, twitter_description: str, twitter_image: str) -> str:
    replacements = [
        (r"<title>.*?</title>", f"<title>{html.escape(title)}</title>"),
        (r'<meta name="description" content=".*?"\s*/?>', f'<meta name="description" content="{html.escape(description)}" />'),
        (r'<link rel="canonical" href=".*?"\s*/?>', f'<link rel="canonical" href="{html.escape(canonical)}" />'),
        (r'<meta property="og:title" content=".*?"\s*/?>', f'<meta property="og:title" content="{html.escape(og_title)}" />'),
        (r'<meta property="og:description" content=".*?"\s*/?>', f'<meta property="og:description" content="{html.escape(og_description)}" />'),
        (r'<meta property="og:url" content=".*?"\s*/?>', f'<meta property="og:url" content="{html.escape(og_url)}" />'),
        (r'<meta property="og:image" content=".*?"\s*/?>', f'<meta property="og:image" content="{html.escape(og_image)}" />'),
        (r'<meta name="twitter:title" content=".*?"\s*/?>', f'<meta name="twitter:title" content="{html.escape(twitter_title)}" />'),
        (r'<meta name="twitter:description" content=".*?"\s*/?>', f'<meta name="twitter:description" content="{html.escape(twitter_description)}" />'),
        (r'<meta name="twitter:image" content=".*?"\s*/?>', f'<meta name="twitter:image" content="{html.escape(twitter_image)}" />'),
    ]
    out = template_html
    for pattern, replacement in replacements:
        out = re.sub(pattern, replacement, out, flags=re.I | re.S)
    return out


def meta_line(parts: list[str]) -> str:
    parts = [p for p in parts if p]
    out = []
    for i, part in enumerate(parts):
        if i:
            out.append('<span class="dot" aria-hidden="true"></span>')
        out.append(part)
    return "".join(out)


def tags_buttons(tags: list[str]) -> str:
    if not tags:
        return ""
    buttons = ''.join(
        f'<button class="tag" type="button" data-tag="{html.escape(tag)}">{html.escape(tag)}</button>'
        for tag in tags
    )
    return f'<div class="tag-row">{buttons}</div>'


def media_markup(post: dict) -> str:
    media_type = post.get("mediaType")
    media_url = post.get("mediaUrl")
    if not media_type or not media_url:
        return ""
    alt = html.escape(post.get("title", "Post image"))
    safe_url = html.escape(media_url)
    if media_type == "image":
        return f'''
        <div class="post-media">
          <img src="{safe_url}" alt="{alt}" loading="lazy" />
        </div>'''
    if media_type == "video":
        return f'''
        <div class="post-media">
          <video controls preload="metadata">
            <source src="{safe_url}" />
          </video>
        </div>'''
    return ""


def latest_card(post: dict) -> str:
    meta_parts = []
    if post.get("author"):
        meta_parts.append(f"<span>{html.escape(post['author'])}</span>")
    if post.get("date"):
        meta_parts.append(f'<time datetime="{html.escape(post["date"])}">{html.escape(post["formatted_date"])}</time>')
    if post.get("tags"):
        meta_parts.append(f"<span>{html.escape(', '.join(post['tags']))}</span>")

    title = html.escape(post.get("title", "Untitled"))
    excerpt = f'<p class="post-excerpt">{html.escape(post.get("excerpt", ""))}</p>' if post.get("excerpt") else ''
    body = f'<div class="post-body">{post.get("content", "")}</div>' if post.get("content") else ''
    share_text = html.escape(post.get("excerpt", ""))
    tags_attr = html.escape("|".join(post.get("tags", [])))
    search_attr = html.escape(post["search_text"])
    slug = html.escape(post["slug"])
    permalink = html.escape(post["permalink"])

    return f'''
      <article class="post-card" id="{slug}" data-post-card data-search="{search_attr}" data-tags="{tags_attr}">
        <div class="post-meta">{meta_line(meta_parts)}</div>
        <h3 class="post-title"><a href="posts/{quote(post["slug"])}.html">{title}</a></h3>
        {excerpt}
        {media_markup(post)}
        {tags_buttons(post.get("tags", []))}
        {body}
        <div class="post-actions">
          <button class="share-button" type="button" data-share-url="{permalink}" data-share-title="{title}" data-share-text="{share_text}">Share</button>
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

    title = html.escape(post.get("title", "Untitled"))
    excerpt = f'<p class="archive-excerpt">{html.escape(post.get("excerpt", ""))}</p>' if post.get("excerpt") else ''
    body = f'<div class="post-body">{post.get("content", "")}</div>' if post.get("content") else ''
    share_text = html.escape(post.get("excerpt", ""))
    tags_attr = html.escape("|".join(post.get("tags", [])))
    search_attr = html.escape(post["search_text"])
    slug = html.escape(post["slug"])
    permalink = html.escape(post["permalink"])

    return f'''
      <article class="archive-item" id="{slug}" data-post-card data-search="{search_attr}" data-tags="{tags_attr}">
        <div class="archive-meta">{meta_line(meta_parts)}</div>
        <h2><a href="posts/{quote(post["slug"])}.html">{title}</a></h2>
        {excerpt}
        {media_markup(post)}
        {tags_buttons(post.get("tags", []))}
        {body}
        <div class="post-actions">
          <button class="share-button" type="button" data-share-url="{permalink}" data-share-title="{title}" data-share-text="{share_text}">Share</button>
        </div>
      </article>
    '''


def inject_index_runtime(html_in: str) -> str:
    runtime = """
  <script>
    (() => {
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

      const makeButton = (tag, isActive = false) => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'tag' + (isActive ? ' active' : '');
        button.textContent = tag;
        return button;
      };

      const renderTags = () => {
        if (!tagCloud) return;
        tagCloud.innerHTML = '';
        if (!allTags.length) {
          tagCloud.innerHTML = '<div class="empty">No tags yet.</div>';
          return;
        }
        const all = makeButton('All', !activeTag);
        all.addEventListener('click', () => {
          activeTag = '';
          render();
        });
        tagCloud.appendChild(all);

        allTags.forEach(tag => {
          const button = makeButton(tag, activeTag === tag);
          button.addEventListener('click', () => {
            activeTag = activeTag === tag ? '' : tag;
            render();
          });
          tagCloud.appendChild(button);
        });
      };

      const matches = (post) => {
        const haystack = (post.dataset.search || '').toLowerCase();
        const tags = (post.dataset.tags || '').split('|').map(t => t.trim()).filter(Boolean);
        const queryMatch = !query || haystack.includes(query);
        const tagMatch = !activeTag || tags.includes(activeTag);
        return queryMatch && tagMatch;
      };

      const render = () => {
        let visible = 0;
        posts.forEach(post => {
          const show = matches(post);
          post.style.display = show ? '' : 'none';
          if (show) visible += 1;
        });
        if (resultsLabel) {
          resultsLabel.textContent = visible ? `Showing ${visible} latest post${visible === 1 ? '' : 's'}` : 'No matching posts';
        }
        renderTags();
      };

      if (searchInput) {
        searchInput.addEventListener('input', (event) => {
          query = String(event.target.value || '').trim().toLowerCase();
          render();
        });
      }

      document.addEventListener('click', async (event) => {
        const button = event.target.closest('.share-button');
        if (!button) return;
        const url = button.dataset.shareUrl;
        const title = button.dataset.shareTitle || 'Post';
        const text = button.dataset.shareText || '';
        try {
          if (navigator.share) {
            await navigator.share({ title, text, url });
          } else {
            await navigator.clipboard.writeText(url);
            const original = button.textContent;
            button.textContent = 'Link Copied';
            setTimeout(() => { button.textContent = original; }, 1800);
          }
        } catch (error) {
          console.error('Share failed:', error);
        }
      });

      render();
    })();
  </script>
</body>
</html>
"""
    return html_in.replace("</body>\n</html>", runtime).replace("</body></html>", runtime)


def inject_archive_runtime(html_in: str) -> str:
    runtime = """
  <script>
    (() => {
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

      const makeButton = (tag, isActive = false) => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'tag' + (isActive ? ' active' : '');
        button.textContent = tag;
        return button;
      };

      const renderTags = () => {
        if (!tagCloud) return;
        tagCloud.innerHTML = '';
        if (!allTags.length) {
          tagCloud.innerHTML = '<div class="empty">No tags yet.</div>';
          return;
        }
        const all = makeButton('All', !activeTag);
        all.addEventListener('click', () => {
          activeTag = '';
          render();
        });
        tagCloud.appendChild(all);

        allTags.forEach(tag => {
          const button = makeButton(tag, activeTag === tag);
          button.addEventListener('click', () => {
            activeTag = activeTag === tag ? '' : tag;
            render();
          });
          tagCloud.appendChild(button);
        });
      };

      const matches = (post) => {
        const haystack = (post.dataset.search || '').toLowerCase();
        const tags = (post.dataset.tags || '').split('|').map(t => t.trim()).filter(Boolean);
        const queryMatch = !query || haystack.includes(query);
        const tagMatch = !activeTag || tags.includes(activeTag);
        return queryMatch && tagMatch;
      };

      const render = () => {
        let visible = 0;
        posts.forEach(post => {
          const show = matches(post);
          post.style.display = show ? '' : 'none';
          if (show) visible += 1;
        });
        if (resultsLabel) {
          resultsLabel.textContent = visible ? `Showing ${visible} post${visible === 1 ? '' : 's'}` : 'No matching posts';
        }
        renderTags();

        if (window.location.hash) {
          const target = document.querySelector(window.location.hash);
          if (target && target.style.display !== 'none') {
            setTimeout(() => {
              target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 120);
          }
        }
      };

      if (searchInput) {
        searchInput.addEventListener('input', (event) => {
          query = String(event.target.value || '').trim().toLowerCase();
          render();
        });
      }

      document.addEventListener('click', async (event) => {
        const button = event.target.closest('.share-button');
        if (!button) return;
        const url = button.dataset.shareUrl;
        const title = button.dataset.shareTitle || 'Post';
        const text = button.dataset.shareText || '';
        try {
          if (navigator.share) {
            await navigator.share({ title, text, url });
          } else {
            await navigator.clipboard.writeText(url);
            const original = button.textContent;
            button.textContent = 'Link Copied';
            setTimeout(() => { button.textContent = original; }, 1800);
          }
        } catch (error) {
          console.error('Share failed:', error);
        }
      });

      render();
    })();
  </script>
</body>
</html>
"""
    return html_in.replace("</body>\n</html>", runtime).replace("</body></html>", runtime)


def inject_post_runtime(html_in: str) -> str:
    runtime = """
  <script>
    (() => {
      const year = document.getElementById('year');
      if (year) year.textContent = new Date().getFullYear();

      document.addEventListener('click', async (event) => {
        const button = event.target.closest('.share-button');
        if (!button) return;
        const url = button.dataset.shareUrl;
        const title = button.dataset.shareTitle || document.title;
        const text = button.dataset.shareText || '';
        try {
          if (navigator.share) {
            await navigator.share({ title, text, url });
          } else {
            await navigator.clipboard.writeText(url);
            const original = button.textContent;
            button.textContent = 'Link Copied';
            setTimeout(() => { button.textContent = original; }, 1800);
          }
        } catch (error) {
          console.error('Share failed:', error);
        }
      });
    })();
  </script>
</body>
</html>
"""
    return html_in.replace("</body>\n</html>", runtime).replace("</body></html>", runtime)


def render_index(posts: list[dict]) -> str:
    template = remove_old_runtime(read_text(INDEX_TEMPLATE))
    latest_cards = "\n".join(latest_card(post) for post in posts[:6])

    if INDEX_POSTS_MARKER not in template:
        raise ValueError(f'Could not find {INDEX_POSTS_MARKER} in index_template.html')

    out = template.replace(INDEX_POSTS_MARKER, f'<div class="posts" id="postsContainer">\n{latest_cards}\n</div>')
    first_image = posts[0].get("mediaUrl", "") if posts else ""
    out = set_meta(
        out,
        title=f"{SITE_NAME} | Fletcher Christian KC",
        description="Personal writing from Fletcher Christian KC. Latest posts, searchable archive, and tag-based browsing in a clean static build.",
        canonical=f"{SITE_URL}/",
        og_title=f"{SITE_NAME} | Fletcher Christian KC",
        og_description="Personal writing from Fletcher Christian KC.",
        og_url=f"{SITE_URL}/",
        og_image=first_image,
        twitter_title=f"{SITE_NAME} | Fletcher Christian KC",
        twitter_description="Personal writing from Fletcher Christian KC.",
        twitter_image=first_image,
    )
    return inject_index_runtime(out)


def render_archive(posts: list[dict]) -> str:
    template = remove_old_runtime(read_text(ARCHIVE_TEMPLATE))
    archive_cards_html = "\n".join(archive_card(post) for post in posts)

    if ARCHIVE_POSTS_MARKER not in template:
        raise ValueError(f'Could not find {ARCHIVE_POSTS_MARKER} in archive_template.html')

    out = template.replace(ARCHIVE_POSTS_MARKER, f'<div id="archiveContainer">\n{archive_cards_html}\n</div>')
    first_image = posts[0].get("mediaUrl", "") if posts else ""
    out = set_meta(
        out,
        title=f"{SITE_NAME} Archive | Fletcher Christian KC",
        description="Full archive of writing from Fletcher Christian KC. Search and filter posts from one shared static posts file.",
        canonical=f"{SITE_URL}/archive.html",
        og_title=f"{SITE_NAME} Archive | Fletcher Christian KC",
        og_description="Full archive of writing from Fletcher Christian KC.",
        og_url=f"{SITE_URL}/archive.html",
        og_image=first_image,
        twitter_title=f"{SITE_NAME} Archive | Fletcher Christian KC",
        twitter_description="Full archive of writing from Fletcher Christian KC.",
        twitter_image=first_image,
    )
    return inject_archive_runtime(out)


def render_post(post: dict) -> str:
    template = remove_old_runtime(read_text(POST_TEMPLATE))
    title = html.escape(post.get("title", "Untitled"))
    excerpt = html.escape(post.get("excerpt", ""))
    share_text = excerpt

    article = f'''
      <article class="archive-item" id="{html.escape(post["slug"])}">
        <div class="archive-meta">
          {meta_line([
            f"<span>{html.escape(post.get('author', ''))}</span>" if post.get('author') else "",
            f'<time datetime="{html.escape(post.get("date", ""))}">{html.escape(post.get("formatted_date", ""))}</time>' if post.get('date') else "",
            f"<span>{html.escape(', '.join(post.get('tags', [])))}</span>" if post.get('tags') else "",
          ])}
        </div>
        <h2>{title}</h2>
        <p class="archive-excerpt">{excerpt}</p>
        {media_markup(post)}
        {tags_buttons(post.get("tags", []))}
        <div class="post-body">{post.get("content", "")}</div>
        <div class="post-actions">
          <button class="share-button" type="button" data-share-url="{html.escape(post["permalink"])}" data-share-title="{title}" data-share-text="{share_text}">Share</button>
          <a class="share-button" href="../archive.html">Archive</a>
        </div>
      </article>
    '''

    out = template.replace('href="index.html"', 'href="../index.html"')
    out = out.replace('href="archive.html"', 'href="../archive.html"')

    if ARCHIVE_POSTS_MARKER not in out:
        raise ValueError(f'Could not find {ARCHIVE_POSTS_MARKER} in post_template.html')
    out = out.replace(ARCHIVE_POSTS_MARKER, f'<div id="archiveContainer">\n{article}\n</div>')

    out = re.sub(
        r'(<div class="eyebrow">[\s\S]*?</div>\s*<h1>)([\s\S]*?)(</h1>)',
        rf'\1{title}\3',
        out,
        count=1,
        flags=re.I,
    )

    out = set_meta(
        out,
        title=f'{post.get("title", "Post")} | Fletcher Christian KC',
        description=post.get("excerpt", ""),
        canonical=post["permalink"],
        og_title=f'{post.get("title", "Post")} | Fletcher Christian KC',
        og_description=post.get("excerpt", ""),
        og_url=post["permalink"],
        og_image=post.get("mediaUrl", ""),
        twitter_title=f'{post.get("title", "Post")} | Fletcher Christian KC',
        twitter_description=post.get("excerpt", ""),
        twitter_image=post.get("mediaUrl", ""),
    )

    article_json = json.dumps({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": post.get("title", ""),
        "description": post.get("excerpt", ""),
        "datePublished": post.get("date", ""),
        "author": {"@type": "Person", "name": post.get("author", AUTHOR_NAME)},
        "image": [post.get("mediaUrl", "")] if post.get("mediaUrl") else [],
        "mainEntityOfPage": post["permalink"],
        "publisher": {
            "@type": "Organization",
            "name": "Jam Killer Productions LLC",
            "url": "https://jamkillerproductions.io"
        }
    }, ensure_ascii=False, indent=2)

    out = re.sub(
        r'<script type="application/ld\+json">[\s\S]*?</script>',
        f'<script type="application/ld+json">\n{article_json}\n  </script>',
        out,
        count=1,
        flags=re.I,
    )

    return inject_post_runtime(out)


def main() -> None:
    if not POSTS_JSON.exists():
        raise FileNotFoundError("posts.json not found in site root.")
    if not INDEX_TEMPLATE.exists():
        raise FileNotFoundError("templates/index_template.html not found.")
    if not ARCHIVE_TEMPLATE.exists():
        raise FileNotFoundError("templates/archive_template.html not found.")
    if not POST_TEMPLATE.exists():
        raise FileNotFoundError("templates/post_template.html not found. Create it by copying archive_template.html.")

    posts = load_posts()

    write_text(ROOT / "index.html", render_index(posts))
    write_text(ROOT / "archive.html", render_archive(posts))

    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    for post in posts:
        write_text(POSTS_DIR / f"{post['slug']}.html", render_post(post))

    print(f"Built {len(posts)} posts.")
    print("Generated:")
    print(f"  {ROOT / 'index.html'}")
    print(f"  {ROOT / 'archive.html'}")
    print(f"  {POSTS_DIR}/")


if __name__ == "__main__":
    main()
