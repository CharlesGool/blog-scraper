# blog-scraper

把 Halo 博客的所有文章抓下来，转换成标准 Markdown（Obsidian 风格笔记库），
正文里用到的图片会按文章分文件夹一起下载到本地，图片链接自动改写为相对路径。

## 输出结构

```
output/
  some-post-slug.md
  some-post-slug/
    image-xxxx.png   # 仅该文章用到的图片
  another-post.md
  another-post/
    ...
```

每篇文章的 Markdown 都带 frontmatter：

```markdown
---
title: "文章标题"
date: 2026-01-01T12:00:00.000Z
source: http://192.168.0.2:8090/archives/some-post-slug
---

正文内容...
```

## 依赖

```bash
pip install requests beautifulsoup4 markdownify
```

## 用法

```bash
python3 scrape_blog.py --base-url http://192.168.0.2:8090 --output ~/blog-backup
```

参数：

| 参数 | 说明 | 默认值 |
|---|---|---|
| `--base-url` | 博客根地址（必填） | - |
| `--output` | 输出目录（必填） | - |
| `--delay` | 每次请求之间的间隔秒数，避免给博客服务器太大压力 | `0.3` |

## 原理

1. 访问 `<base-url>/archives` 页面，解析出所有文章的 slug 列表。
2. 依次访问每篇文章的 `/archives/<slug>` 页面，提取标题、发布时间和正文
   （`article.post-content .markdown-body`）。
3. 把正文里的 `<img>` 下载到 `output/<slug>/` 目录下，并将 `src` 改写成
   相对路径，保证脱离原博客后 Markdown 也能正常显示图片。
4. 把 HTML 正文转换为 Markdown，写入 `output/<slug>.md`。

## 局限性

- 仅针对 Halo 主题的默认页面结构（`#seo-header`、
  `article.post-content .markdown-body` 等选择器）做了适配，其他主题
  可能需要调整选择器。
- 不会抓取分类、标签、评论等元数据，只保留标题、发布时间和正文。
- 未做登录鉴权，仅适用于公开可访问的文章。
