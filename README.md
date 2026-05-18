# Blog Generator

A lightweight Python static site generator for personal blogs. Write posts as HTML with YAML front matter, build to a `dist/` folder, and optionally publish to AWS S3 + CloudFront.

## Features

- Posts as HTML files with YAML front matter
- Jinja2 templates with dark/light theme support
- Automatic category and type index pages
- Optional link shortener (`/links/go/?link=name`)
- One-command publish to S3 with CloudFront cache invalidation

## Setup

```bash
# Clone the repo
git clone https://github.com/your-username/blog-generator.git
cd blog-generator

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure site name and description
# Edit the SITE_NAME and SITE_DESCRIPTION constants at the top of build.py

# Copy the env template and fill in your AWS credentials (only needed for publishing)
cp .env.example .env
```

## Writing Posts

Create a `.html` file in `posts/` with YAML front matter:

```html
---
title: "My First Post"
date: 2025-01-01
categories: [General]
type: Tutorial
description: A short summary of the post.
author: Your Name
draft: false
---

<p>Post content goes here as plain HTML.</p>
```

**Front matter fields:**

| Field | Required | Description |
|-------|----------|-------------|
| `title` | Yes | Post title |
| `date` | Yes | Publication date (`YYYY-MM-DD`) |
| `categories` | No | List of category tags |
| `type` | No | Post type label (e.g. Tutorial, Review) |
| `description` | No | Short summary shown in listings |
| `author` | No | Author name |
| `draft` | No | Set `true` to exclude from build |
| `slug` | No | URL override; defaults to filename |

To add images, place them in `images/your-post-slug/` and reference them with an absolute path in the post HTML:

```html
<img src="/images/my-first-post/screenshot.png" alt="Screenshot">
```

## Building

```bash
python3 build.py
```

Output goes to `dist/`. Preview locally:

```bash
sh serve.sh
# Open http://localhost:8080
```

## Publishing to S3

Fill in your `.env` file:

```
AWS_BUCKET_NAME=your-s3-bucket-name
AWS_REGION=us-east-1
CLOUDFRONT_DISTRIBUTION_ID=   # optional
AWS_ACCESS_KEY_ID=             # optional if using ~/.aws/credentials
AWS_SECRET_ACCESS_KEY=         # optional if using ~/.aws/credentials
```

Then:

```bash
python3 build.py && python3 publish.py
```

`publish.py` compares MD5 hashes to skip unchanged files, deletes files removed from `dist/`, and optionally invalidates the CloudFront distribution cache.

## Link Shortener

Add entries to `data/links.json`:

```json
[
  {
    "name": "my-link",
    "type": "informational",
    "url": "https://example.com",
    "description": "A description of the link."
  }
]
```

Links are accessible at `/links/go/?link=my-link`.

## Customization

- **Templates** — edit files in `templates/` (Jinja2)
- **Styles** — edit `static/style.css`
- **JavaScript** — edit `static/script.js`
- **Site name/description** — edit `SITE_NAME` and `SITE_DESCRIPTION` at the top of `build.py`
