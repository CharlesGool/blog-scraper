#!/usr/bin/env python3
"""
Scrape a Halo-powered blog into an Obsidian-style Markdown vault:
    output/
      <slug>.md
      <slug>/
        image-xxxx.png   (images used only by that post)

Usage:
    python3 scrape_blog.py --base-url http://192.168.0.2:8090 --output ~/blog-backup
"""
import argparse
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as html_to_md

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def get(session, url):
    resp = session.get(url, headers={"User-Agent": UA}, timeout=15)
    resp.raise_for_status()
    return resp


def get_soup(session, url):
    resp = get(session, url)
    # Server doesn't send a charset in Content-Type, so let BeautifulSoup
    # sniff it from the page's own <meta charset> instead of trusting
    # requests' ISO-8859-1 fallback (which mangles Chinese text).
    return BeautifulSoup(resp.content, "html.parser"), resp


def list_post_slugs(session, base_url):
    soup, _ = get_soup(session, urljoin(base_url, "/archives"))
    slugs = []
    seen = set()
    for a in soup.select('a[href^="/archives/"]'):
        href = a["href"].split("?")[0].rstrip("/")
        slug = href.rsplit("/", 1)[-1]
        if slug and slug not in seen and href.count("/") == 2:
            seen.add(slug)
            slugs.append(slug)
    return slugs


def sanitize_filename(name):
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    return name.strip() or "untitled"


def scrape_post(session, base_url, slug, output_dir):
    url = urljoin(base_url, f"/archives/{slug}")
    soup, _ = get_soup(session, url)

    h1 = soup.select_one("#seo-header")
    title = h1.get_text(strip=True) if h1 else slug

    time_tag = soup.select_one("time[datetime]")
    date = time_tag["datetime"] if time_tag and time_tag.has_attr("datetime") else ""

    content = soup.select_one("article.post-content .markdown-body")
    if content is None:
        print(f"  ! 未找到正文内容,跳过: {slug}")
        return

    asset_dir = output_dir / slug
    img_tags = content.find_all("img")
    if img_tags:
        asset_dir.mkdir(parents=True, exist_ok=True)

    for img in img_tags:
        src = img.get("src")
        if not src:
            continue
        img_url = urljoin(url, src)
        filename = sanitize_filename(Path(urlparse(img_url).path).name) or "image.png"
        local_path = asset_dir / filename
        if not local_path.exists():
            try:
                r = get(session, img_url)
                local_path.write_bytes(r.content)
            except Exception as e:
                print(f"  ! 图片下载失败 {img_url}: {e}")
                continue
        img["src"] = f"{slug}/{filename}"

    md_body = html_to_md(str(content), heading_style="ATX", bullets="-")
    md_body = re.sub(r"\n{3,}", "\n\n", md_body).strip()

    frontmatter = (
        "---\n"
        f"title: \"{title}\"\n"
        f"date: {date}\n"
        f"source: {url}\n"
        "---\n\n"
    )

    md_path = output_dir / f"{sanitize_filename(slug)}.md"
    md_path.write_text(frontmatter + md_body + "\n", encoding="utf-8")
    print(f"  ✓ {slug} -> {md_path.name} ({len(img_tags)} 张图片)")


def main():
    parser = argparse.ArgumentParser(description="把 Halo 博客爬成 Obsidian 风格的 Markdown 笔记库")
    parser.add_argument("--base-url", required=True, help="博客根地址,如 http://192.168.0.2:8090")
    parser.add_argument("--output", required=True, help="输出目录")
    parser.add_argument("--delay", type=float, default=0.3, help="请求间隔秒数,默认 0.3")
    args = parser.parse_args()

    output_dir = Path(args.output).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    print(f"正在获取文章列表: {args.base_url}/archives")
    slugs = list_post_slugs(session, args.base_url)
    print(f"共发现 {len(slugs)} 篇文章\n")

    for i, slug in enumerate(slugs, 1):
        print(f"[{i}/{len(slugs)}] {slug}")
        try:
            scrape_post(session, args.base_url, slug, output_dir)
        except Exception as e:
            print(f"  ! 抓取失败: {e}")
        time.sleep(args.delay)

    print(f"\n完成,输出目录: {output_dir}")


if __name__ == "__main__":
    main()
