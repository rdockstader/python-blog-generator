#!/usr/bin/env python3
"""
Sync dist/ to S3, uploading new/changed files and removing deleted ones.
Unchanged files (matching ETag/MD5) are skipped.
If CLOUDFRONT_DISTRIBUTION_ID is set and files changed, the distribution
cache is invalidated automatically.

Usage:
  python3 publish.py

Requires a .env file (or environment variables) with:
  AWS_BUCKET_NAME             - S3 bucket name
  AWS_REGION                  - AWS region (e.g. us-east-1)
  CLOUDFRONT_DISTRIBUTION_ID  - optional; triggers cache invalidation if set
  AWS_ACCESS_KEY_ID           - optional if using ~/.aws/credentials or IAM role
  AWS_SECRET_ACCESS_KEY       - optional if using ~/.aws/credentials or IAM role
"""

import hashlib
import mimetypes
import os
import sys
import time
from pathlib import Path

import boto3
from boto3.s3.transfer import TransferConfig
from dotenv import load_dotenv

load_dotenv()

DIST_DIR = Path("dist")

# Keep uploads single-part (up to 100 MB) so ETag == MD5 for comparison
_TRANSFER_CONFIG = TransferConfig(multipart_threshold=100 * 1024 * 1024)

# Explicit MIME overrides for types Python sometimes misses
_MIME_OVERRIDES = {
    ".js":   "application/javascript",
    ".css":  "text/css",
    ".svg":  "image/svg+xml",
    ".ico":  "image/x-icon",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
}


def _require_env(name: str) -> str:
    val = os.getenv(name)
    if not val:
        sys.exit(f"ERROR: {name} is not set. Add it to .env or your environment.")
    return val


def _md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65_536), b""):
            h.update(chunk)
    return h.hexdigest()


def _content_type(path: Path) -> str:
    override = _MIME_OVERRIDES.get(path.suffix.lower())
    if override:
        return override
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "application/octet-stream"


def _list_bucket(s3, bucket: str) -> dict[str, str]:
    """Return {key: etag_hex} for every object in the bucket."""
    paginator = s3.get_paginator("list_objects_v2")
    objects: dict[str, str] = {}
    for page in paginator.paginate(Bucket=bucket):
        for obj in page.get("Contents", []):
            etag = obj["ETag"].strip('"')
            objects[obj["Key"]] = etag
    return objects


def publish() -> None:
    bucket = _require_env("AWS_BUCKET_NAME")
    region = os.getenv("AWS_REGION")

    s3 = boto3.client(
        "s3",
        region_name=region,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID") or None,
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY") or None,
    )

    if not DIST_DIR.exists():
        sys.exit(f"ERROR: {DIST_DIR}/ does not exist. Run build.py first.")

    print(f"Scanning s3://{bucket}/ …")
    remote = _list_bucket(s3, bucket)

    print(f"Scanning {DIST_DIR}/ …")
    local: dict[str, Path] = {}
    for path in DIST_DIR.rglob("*"):
        if path.is_file():
            key = path.relative_to(DIST_DIR).as_posix()
            local[key] = path

    to_upload: list[tuple[str, Path]] = []
    skipped: list[str] = []

    for key, path in sorted(local.items()):
        remote_etag = remote.get(key)
        if remote_etag and remote_etag == _md5(path):
            skipped.append(key)
        else:
            to_upload.append((key, path))

    to_delete = sorted(key for key in remote if key not in local)

    print(f"\n  {len(to_upload)} to upload, {len(to_delete)} to delete, {len(skipped)} unchanged\n")

    for key, path in to_upload:
        ct = _content_type(path)
        s3.upload_file(
            str(path),
            bucket,
            key,
            ExtraArgs={"ContentType": ct},
            Config=_TRANSFER_CONFIG,
        )
        print(f"  ↑ {key}")

    if to_delete:
        for i in range(0, len(to_delete), 1000):
            batch = [{"Key": k} for k in to_delete[i : i + 1000]]
            s3.delete_objects(Bucket=bucket, Delete={"Objects": batch})
        for key in to_delete:
            print(f"  ✕ {key}")

    print(f"\nDone. {len(to_upload)} uploaded, {len(to_delete)} deleted, {len(skipped)} unchanged.")

    cf_distribution = os.getenv("CLOUDFRONT_DISTRIBUTION_ID")
    if cf_distribution and (to_upload or to_delete):
        print(f"\nInvalidating CloudFront distribution {cf_distribution} …")
        cf = boto3.client(
            "cloudfront",
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID") or None,
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY") or None,
        )
        cf.create_invalidation(
            DistributionId=cf_distribution,
            InvalidationBatch={
                "Paths": {"Quantity": 1, "Items": ["/*"]},
                "CallerReference": str(int(time.time())),
            },
        )
        print("  ✓ Invalidation created (changes will propagate in ~30–60s)")


if __name__ == "__main__":
    publish()
