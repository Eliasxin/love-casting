#!/usr/bin/env python3
"""Sync *only* published, website-public Love Casting articles from Notion.

Required environment variables:
  NOTION_TOKEN          Notion internal integration token
  NOTION_DATABASE_ID    ID of the existing shared 📖 章節資料庫
  NOTION_WORK_PAGE_ID   ID of the 戀愛 Casting page in 📚 我的作品

Private drafts are excluded before body requests, and never written to disk.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

API = "https://api.notion.com/v1"
API_VERSION = "2022-06-28"
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "chapters.json"
MEDIA = ROOT / "assets" / "notion"
PUBLISHED = {"已發布", "已發佈", "published", "公開", "已上線"}
MAX_MEDIA_BYTES = 12 * 1024 * 1024


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing GitHub Actions secret/environment variable: {name}")
    return value


def request_json(method: str, path: str, payload: dict | None = None) -> dict:
    token = required_env("NOTION_TOKEN")
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    req = Request(
        API + path,
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": API_VERSION,
            "Content-Type": "application/json",
        },
    )
    for attempt in range(5):
        try:
            with urlopen(req, timeout=35) as resp:
                return json.load(resp)
        except HTTPError as exc:
            message = exc.read().decode("utf-8", errors="replace")[:450]
            if exc.code in (429, 500, 502, 503, 504) and attempt < 4:
                retry = exc.headers.get("Retry-After")
                time.sleep(min(int(retry), 20) if retry and retry.isdigit() else 2 ** attempt)
                continue
            if exc.code in (403, 404):
                raise RuntimeError(
                    f"Notion {exc.code} at {path}. Check database/page ID and share the database with your Notion integration. {message}"
                ) from exc
            raise RuntimeError(f"Notion API {exc.code} at {path}: {message}") from exc
        except URLError as exc:
            if attempt < 4:
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"Network failure fetching {path}: {exc}") from exc
    raise AssertionError("Unreachable retry state")


def all_pages(database_id: str) -> list[dict]:
    rows, cursor = [], None
    while True:
        payload = {"page_size": 100}
        if cursor:
            payload["start_cursor"] = cursor
        result = request_json("POST", f"/databases/{database_id}/query", payload)
        rows.extend(result.get("results", []))
        cursor = result.get("next_cursor")
        if not result.get("has_more") or not cursor:
            return rows


def property_of(page: dict, *names: str) -> dict:
    props = page.get("properties") or {}
    for name in names:
        if name in props:
            return props[name] or {}
    return {}


def richtext_plain(runs: list[dict] | None) -> str:
    return "".join(run.get("plain_text", run.get("text", {}).get("content", "")) or "" for run in (runs or []))


def value(prop: dict) -> str:
    t = prop.get("type")
    if t in ("select", "status"):
        return str((prop.get(t) or {}).get("name") or "").strip()
    if t in ("title", "rich_text"):
        return richtext_plain(prop.get(t)).strip()
    if t == "number":
        number = prop.get("number")
        return "" if number is None else str(number)
    if t == "formula":
        val = prop.get("formula") or {}
        return str(val.get(val.get("type"), "") or "").strip()
    if t == "multi_select":
        return "、".join(item.get("name", "") for item in prop.get("multi_select", []))
    return ""


def page_title(page: dict) -> str:
    prop = property_of(page, "文章名稱", "Name", "名稱", "標題", "Title")
    if prop.get("type") == "title":
        return value(prop)
    for prop in (page.get("properties") or {}).values():
        if prop.get("type") == "title":
            return value(prop)
    return ""


def is_published(page: dict) -> bool:
    status = value(property_of(page, "發布狀態", "發佈狀態", "狀態")).casefold()
    is_public = property_of(page, "網站公開").get("checkbox") is True
    return status in PUBLISHED and is_public


def belongs_to_work(page: dict, work_id: str) -> bool:
    prop = property_of(page, "所屬作品")
    if prop.get("type") != "relation":
        return False
    normalize = lambda identifier: re.sub(r"[^a-f0-9]", "", identifier.casefold())
    return any(normalize(link.get("id", "")) == normalize(work_id) for link in prop.get("relation", []))


def get_number(page: dict) -> int | None:
    prop = property_of(page, "章節順序", "章節編號", "排序")
    t = prop.get("type")
    raw = prop.get("number") if t == "number" else value(prop)
    if raw is None or str(raw).strip() == "":
        return None
    try:
        number = float(raw)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid chapter order for {page_title(page)!r}: {raw!r}")
    if not number.is_integer() or number < 0:
        raise ValueError(f"Chapter order must be a nonnegative whole number for {page_title(page)!r}")
    return int(number)


def runs_of(block_part: dict) -> list[dict]:
    runs=[]
    for rt in (block_part.get("rich_text") or []):
        a=rt.get("annotations") or {}
        href=rt.get("href")
        if not href and rt.get("type")=="text":
            href=(rt.get("text") or {}).get("link") or {}
            href=href.get("url") if isinstance(href,dict) else None
        runs.append({
            "text": rt.get("plain_text", (rt.get("text") or {}).get("content", "")),
            "bold": bool(a.get("bold")), "italic": bool(a.get("italic")),
            "underline": bool(a.get("underline")), "strikethrough": bool(a.get("strikethrough")),
            "code": bool(a.get("code")), "href": href or None,
        })
    return runs


def block_children(block_id: str) -> list[dict]:
    items, cursor = [], None
    while True:
        path = f"/blocks/{block_id}/children?page_size=100"
        if cursor:
            path += f"&start_cursor={cursor}"
        data = request_json("GET", path)
        items.extend(data.get("results") or [])
        cursor = data.get("next_cursor")
        if not data.get("has_more") or not cursor:
            return items


def image_from_notion(block: dict) -> str | None:
    image = block.get("image") or {}
    subtype = image.get("type")
    url = (image.get(subtype) or {}).get("url") if subtype in ("file", "external") else None
    if not url:
        return None
    # External user-provided links remain external. Notion-signed 'file' URLs expire,
    # so localize those to a static asset during the sync.
    if subtype != "file":
        return url if urlparse(url).scheme == "https" else None
    MEDIA.mkdir(parents=True, exist_ok=True)
    identifier = re.sub(r"[^a-f0-9]", "", block.get("id", "").casefold())
    if not identifier:
        identifier = hashlib.sha256(url.encode()).hexdigest()[:20]
    allowed_ext = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix not in allowed_ext:
        suffix = ".jpg"
    target = MEDIA / f"{identifier}{suffix}"
    req = Request(url, headers={"User-Agent": "LoveCastingNotionSync/1.0"})
    try:
        with urlopen(req, timeout=40) as resp:
            mime = resp.headers.get_content_type()
            if mime not in ("image/png", "image/jpeg", "image/webp", "image/gif"):
                raise RuntimeError(f"Unsupported Notion image content type: {mime}")
            mime_extension={"image/png":".png","image/jpeg":".jpg","image/webp":".webp","image/gif":".gif"}[mime]
            target=MEDIA / f"{identifier}{mime_extension}"
            data=resp.read(MAX_MEDIA_BYTES+1)
            if len(data)>MAX_MEDIA_BYTES:
                raise RuntimeError(f"Notion image too large (max 12 MB): {block.get('id')}")
            if not data:
                raise RuntimeError("Notion image is empty")
            # Avoid rewriting identical images (unnecessary deploy/commit).
            if not target.exists() or target.read_bytes()!=data:
                target.write_bytes(data)
            return "./assets/notion/"+target.name
    except (HTTPError,URLError) as exc:
        raise RuntimeError(f"Cannot save Notion image in block {block.get('id')}: {exc}") from exc


def convert_blocks(blocks: list[dict], depth: int = 0) -> list[dict]:
    if depth > 8:
        raise RuntimeError("Notion block nesting is more than eight levels deep")
    converted=[]
    supported={"paragraph","heading_1","heading_2","heading_3","bulleted_list_item","numbered_list_item","to_do","quote","code","callout","toggle","divider","image","table","table_row"}
    for block in blocks:
        kind=block.get("type", "")
        if kind not in supported:
            # Keep reading other blocks; unknown blocks are not published as raw HTML.
            continue
        part=block.get(kind) or {}
        out={"type": kind}
        if kind=="divider":
            converted.append(out)
            continue
        if kind=="image":
            url=image_from_notion(block)
            if url:
                out.update({"url":url,"caption":richtext_plain(part.get("caption"))})
                converted.append(out)
            continue
        if kind=="table_row":
            out["cells"]=[runs_of({"rich_text":cell}) for cell in part.get("cells",[])]
        else:
            out["runs"]=runs_of(part)
        if kind=="to_do":
            out["checked"]=bool(part.get("checked"))
        if block.get("has_children"):
            out["children"]=convert_blocks(block_children(block["id"]),depth+1)
        converted.append(out)
    return converted


def main() -> None:
    database_id = required_env("NOTION_DATABASE_ID")
    work_id = required_env("NOTION_WORK_PAGE_ID")
    pages = all_pages(database_id)
    belonging = [p for p in pages if belongs_to_work(p,work_id)]
    public = [p for p in belonging if is_published(p)]
    print(f"Database records: {len(pages)}; 戀愛 Casting records: {len(belonging)}; public eligible: {len(public)}")
    if not belonging:
        raise RuntimeError("No chapters matched NOTION_WORK_PAGE_ID. Confirm it is the 戀愛 Casting page's Notion ID and that 所屬作品 is linked.")
    chapters=[]
    seen_slugs=set()
    for page in public:
        title=page_title(page).strip()
        slug=value(property_of(page,"網站章節識別碼")).strip()
        if not title:
            raise RuntimeError(f"Public article has no title (Notion page ID {page['id']})")
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*",slug):
            raise RuntimeError(f"Public article {title!r} requires a unique lowercase ASCII 網站章節識別碼 (current {slug!r})")
        if slug in seen_slugs:
            raise RuntimeError(f"Duplicate 網站章節識別碼: {slug!r}")
        seen_slugs.add(slug)
        chapters.append({
            "slug":slug, "title":title,
            "chapterNumber":get_number(page),
            "chapterType":value(property_of(page,"章節類型")),
            "originalScript":value(property_of(page,"原始劇本名稱")),
            "ageRating":value(property_of(page,"閱讀分級")) or "一般",
            "blocks":convert_blocks(block_children(page["id"])),
        })
    chapters.sort(key=lambda c:(c["chapterNumber"] if c["chapterNumber"] is not None else 99999,c["title"]))
    # Avoid needless commits: update date only when content changes.
    payload={"site":"戀愛 Casting：創造出屬於你的劇本","updatedAt":None,"chapters":chapters}
    if OUTPUT.exists():
        try:
            old=json.loads(OUTPUT.read_text(encoding="utf-8"))
            if old.get("chapters")==chapters:
                print(f"No content changes; {len(chapters)} public articles unchanged")
                return
        except (OSError,ValueError):
            pass
    payload["updatedAt"]=dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00","Z")
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Wrote {len(chapters)} publicly available articles to data/chapters.json")
    print("Draft and website-private content was NOT exported")

if __name__=="__main__":
    try:
        main()
    except Exception as exc:
        print(f"Sync failed: {exc}",file=sys.stderr)
        sys.exit(1)
