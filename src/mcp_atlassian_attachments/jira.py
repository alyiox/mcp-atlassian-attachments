from __future__ import annotations

import mimetypes
import re
from typing import Any

import httpx

from .client import check_response, make_client
from .config import AtlassianConfig, load_config
from .fs import resolve_input_path, resolve_output_path, sanitize_filename, stream_to_file

_MEDIA_ID_RE = re.compile(r"/file/([0-9a-fA-F-]{36})/")


def resolve_media_id(client: httpx.Client, cfg: AtlassianConfig, attachment_id: str) -> str | None:
    """Return the Media Services UUID that ADF media nodes use for this attachment.

    An ADF media node references a file by its Media Services UUID, not by the
    numeric Jira attachment ID, and no attachment metadata endpoint exposes it.
    The content endpoint answers with a 303 to the media host, so stopping at the
    redirect yields the UUID without downloading the file. Returns None rather
    than raising: callers have already uploaded or located the attachment, and
    losing that result over a best-effort lookup would be worse than a null.
    """
    url = f"{cfg.base_url}/rest/api/3/attachment/content/{attachment_id}"
    try:
        resp = client.get(url, follow_redirects=False)
    except httpx.HTTPError:
        return None
    match = _MEDIA_ID_RE.search(resp.headers.get("location", ""))
    return match.group(1) if match else None


def download_jira_attachment(
    attachment_id: str,
    output_dir: str,
    filename: str | None = None,
    overwrite: bool = False,
    *,
    cfg: AtlassianConfig | None = None,
) -> dict[str, Any]:
    cfg = cfg or load_config()

    with make_client(cfg) as client:
        meta_url = f"{cfg.base_url}/rest/api/3/attachment/{attachment_id}"
        meta_resp = client.get(meta_url)
        check_response(meta_resp, "Jira attachment metadata")
        meta = meta_resp.json()

        raw_name = filename if filename else meta["filename"]
        safe_name = sanitize_filename(raw_name)
        output_path = resolve_output_path(output_dir, safe_name)

        content_url: str = meta.get("content") or (f"{cfg.base_url}/rest/api/3/attachment/content/{attachment_id}")
        expected_size: int | None = meta.get("size")

        with client.stream("GET", content_url) as resp:
            check_response(resp, "Jira attachment content")
            bytes_written = stream_to_file(resp, output_path, expected_size, overwrite)

    return {
        "product": "jira",
        "attachmentId": attachment_id,
        "filename": safe_name,
        "mimeType": meta.get("mimeType"),
        "size": bytes_written,
        "path": str(output_path),
        "attachmentUrl": content_url,
    }


def upload_jira_attachment(
    issue_key: str,
    file_path: str,
    filename: str | None = None,
    *,
    cfg: AtlassianConfig | None = None,
) -> dict[str, Any]:
    cfg = cfg or load_config()

    source = resolve_input_path(file_path)
    upload_name = sanitize_filename(filename) if filename else sanitize_filename(source.name)
    mime_type = mimetypes.guess_type(upload_name)[0] or "application/octet-stream"
    local_size = source.stat().st_size

    url = f"{cfg.base_url}/rest/api/3/issue/{issue_key}/attachments"

    with make_client(cfg) as client, source.open("rb") as fh:
        # Jira rejects multipart uploads without this header as suspected XSRF.
        resp = client.post(
            url,
            headers={"X-Atlassian-Token": "no-check"},
            files={"file": (upload_name, fh, mime_type)},
        )
        check_response(resp, "Jira attachment upload")
        created = resp.json()

        # The endpoint returns a list of created attachments, one per uploaded file.
        item: dict[str, Any] = created[0] if isinstance(created, list) and created else {}

        attachment_id = item.get("id")
        media_id = resolve_media_id(client, cfg, attachment_id) if attachment_id else None

    stored_name = item.get("filename") or upload_name

    return {
        "product": "jira",
        "issueKey": issue_key,
        "attachmentId": attachment_id,
        "filename": stored_name,
        "mimeType": item.get("mimeType") or mime_type,
        "size": item.get("size", local_size),
        "path": str(source),
        "attachmentUrl": item.get("content"),
        "mediaId": media_id,
    }


def get_jira_attachment_reference(
    attachment_id: str,
    *,
    cfg: AtlassianConfig | None = None,
) -> dict[str, Any]:
    cfg = cfg or load_config()

    with make_client(cfg) as client:
        meta_url = f"{cfg.base_url}/rest/api/3/attachment/{attachment_id}"
        meta_resp = client.get(meta_url)
        check_response(meta_resp, "Jira attachment metadata")
        meta = meta_resp.json()

        media_id = resolve_media_id(client, cfg, attachment_id)

    filename = meta.get("filename") or attachment_id

    return {
        "product": "jira",
        "attachmentId": attachment_id,
        "filename": filename,
        "mimeType": meta.get("mimeType"),
        "size": meta.get("size"),
        "attachmentUrl": meta.get("content") or f"{cfg.base_url}/rest/api/3/attachment/content/{attachment_id}",
        "mediaId": media_id,
    }


def delete_jira_attachment(
    attachment_id: str,
    *,
    cfg: AtlassianConfig | None = None,
) -> dict[str, Any]:
    cfg = cfg or load_config()

    url = f"{cfg.base_url}/rest/api/3/attachment/{attachment_id}"

    with make_client(cfg) as client:
        # Read the metadata first so the caller learns what was removed, and so a
        # missing attachment fails before any delete is attempted.
        meta_resp = client.get(url)
        check_response(meta_resp, "Jira attachment metadata")
        meta = meta_resp.json()

        del_resp = client.delete(url)
        check_response(del_resp, "Jira attachment deletion")

    return {
        "product": "jira",
        "attachmentId": attachment_id,
        "filename": meta.get("filename"),
        "mimeType": meta.get("mimeType"),
        "size": meta.get("size"),
        "deleted": True,
    }
