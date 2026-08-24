from __future__ import annotations

import httpx
import pytest
import respx

from mcp_atlassian_attachments.config import AtlassianConfig
from mcp_atlassian_attachments.jira import (
    delete_jira_attachment,
    download_jira_attachment,
    get_jira_attachment_reference,
    upload_jira_attachment,
)

SITE = "https://test.atlassian.net"
CLOUD_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
CFG = AtlassianConfig(site_url=SITE, email="u@e.com", api_token="tok", cloud_id=CLOUD_ID)

ATTACHMENT_ID = "439535"
BASE = f"https://api.atlassian.com/ex/jira/{CLOUD_ID}"
META_URL = f"{BASE}/rest/api/3/attachment/{ATTACHMENT_ID}"
CONTENT_URL = f"{BASE}/rest/api/3/attachment/content/{ATTACHMENT_ID}"
FILE_CONTENT = b"fake png data"


def _meta(filename="test.png", mime="image/png", size=None, content_url=None):
    meta = {
        "id": ATTACHMENT_ID,
        "filename": filename,
        "mimeType": mime,
        "content": content_url or CONTENT_URL,
    }
    if size is not None:
        meta["size"] = size
    return meta


@respx.mock
def test_downloads_jira_attachment(tmp_path):
    respx.get(META_URL).mock(return_value=httpx.Response(200, json=_meta()))
    respx.get(CONTENT_URL).mock(return_value=httpx.Response(200, content=FILE_CONTENT))

    result = download_jira_attachment(ATTACHMENT_ID, str(tmp_path), cfg=CFG)

    assert result["product"] == "jira"
    assert result["attachmentId"] == ATTACHMENT_ID
    assert result["filename"] == "test.png"
    assert result["mimeType"] == "image/png"
    assert result["size"] == len(FILE_CONTENT)
    saved = tmp_path / "test.png"
    assert saved.exists()
    assert saved.read_bytes() == FILE_CONTENT


@respx.mock
def test_uses_filename_override(tmp_path):
    respx.get(META_URL).mock(return_value=httpx.Response(200, json=_meta()))
    respx.get(CONTENT_URL).mock(return_value=httpx.Response(200, content=FILE_CONTENT))

    result = download_jira_attachment(ATTACHMENT_ID, str(tmp_path), filename="custom.png", cfg=CFG)

    assert result["filename"] == "custom.png"
    assert (tmp_path / "custom.png").exists()


@respx.mock
def test_verifies_size_match(tmp_path):
    respx.get(META_URL).mock(return_value=httpx.Response(200, json=_meta(size=len(FILE_CONTENT))))
    respx.get(CONTENT_URL).mock(return_value=httpx.Response(200, content=FILE_CONTENT))

    result = download_jira_attachment(ATTACHMENT_ID, str(tmp_path), cfg=CFG)

    assert result["size"] == len(FILE_CONTENT)


@respx.mock
def test_size_mismatch_raises(tmp_path):
    respx.get(META_URL).mock(return_value=httpx.Response(200, json=_meta(size=9999)))
    respx.get(CONTENT_URL).mock(return_value=httpx.Response(200, content=FILE_CONTENT))

    with pytest.raises(ValueError, match="mismatch"):
        download_jira_attachment(ATTACHMENT_ID, str(tmp_path), cfg=CFG)


@respx.mock
def test_raises_on_401(tmp_path):
    respx.get(META_URL).mock(return_value=httpx.Response(401))

    with pytest.raises(RuntimeError, match="401"):
        download_jira_attachment(ATTACHMENT_ID, str(tmp_path), cfg=CFG)

    assert "tok" not in str(pytest.raises(RuntimeError))


@respx.mock
def test_raises_on_403(tmp_path):
    respx.get(META_URL).mock(return_value=httpx.Response(403))

    with pytest.raises(RuntimeError, match="403"):
        download_jira_attachment(ATTACHMENT_ID, str(tmp_path), cfg=CFG)


@respx.mock
def test_raises_on_404(tmp_path):
    respx.get(META_URL).mock(return_value=httpx.Response(404))

    with pytest.raises(RuntimeError, match="404"):
        download_jira_attachment(ATTACHMENT_ID, str(tmp_path), cfg=CFG)


@respx.mock
def test_raises_on_existing_file(tmp_path):
    (tmp_path / "test.png").write_bytes(b"existing")
    respx.get(META_URL).mock(return_value=httpx.Response(200, json=_meta()))
    respx.get(CONTENT_URL).mock(return_value=httpx.Response(200, content=FILE_CONTENT))

    with pytest.raises(FileExistsError):
        download_jira_attachment(ATTACHMENT_ID, str(tmp_path), cfg=CFG)


@respx.mock
def test_overwrites_existing_file(tmp_path):
    (tmp_path / "test.png").write_bytes(b"old")
    respx.get(META_URL).mock(return_value=httpx.Response(200, json=_meta()))
    respx.get(CONTENT_URL).mock(return_value=httpx.Response(200, content=FILE_CONTENT))

    result = download_jira_attachment(ATTACHMENT_ID, str(tmp_path), overwrite=True, cfg=CFG)

    assert (tmp_path / "test.png").read_bytes() == FILE_CONTENT
    assert result["size"] == len(FILE_CONTENT)


@respx.mock
def test_creates_output_dir(tmp_path):
    new_dir = tmp_path / "nested" / "dir"
    respx.get(META_URL).mock(return_value=httpx.Response(200, json=_meta()))
    respx.get(CONTENT_URL).mock(return_value=httpx.Response(200, content=FILE_CONTENT))

    download_jira_attachment(ATTACHMENT_ID, str(new_dir), cfg=CFG)

    assert new_dir.is_dir()
    assert (new_dir / "test.png").exists()


@respx.mock
def test_error_does_not_leak_token(tmp_path):
    respx.get(META_URL).mock(return_value=httpx.Response(401))

    with pytest.raises(RuntimeError) as exc_info:
        download_jira_attachment(ATTACHMENT_ID, str(tmp_path), cfg=CFG)

    assert "tok" not in str(exc_info.value)
    assert CFG.email not in str(exc_info.value)


UPLOAD_URL = f"{BASE}/rest/api/3/issue/PROJ-123/attachments"


def _created(filename="upload.png", mime="image/png", size=None, attachment_id="600100"):
    return [
        {
            "id": attachment_id,
            "filename": filename,
            "mimeType": mime,
            "size": size if size is not None else len(FILE_CONTENT),
            "content": f"{SITE}/rest/api/3/attachment/content/{attachment_id}",
        }
    ]


def _local_file(tmp_path, name="upload.png", content=FILE_CONTENT):
    path = tmp_path / name
    path.write_bytes(content)
    return path


MEDIA_ID = "6df94659-caa7-4561-bbe3-6384ec534bba"
UPLOADED_ID = "600100"
UPLOADED_CONTENT_URL = f"{BASE}/rest/api/3/attachment/content/{UPLOADED_ID}"
REF_META_URL = f"{BASE}/rest/api/3/attachment/{UPLOADED_ID}"


def _media_redirect(media_id=MEDIA_ID):
    # Jira answers the content endpoint with a 303 to the media host; the UUID in
    # that path is what ADF media nodes reference.
    return httpx.Response(
        303,
        headers={"location": f"https://api.media.atlassian.com/file/{media_id}/binary?token=redacted"},
    )


@respx.mock
def test_uploads_jira_attachment(tmp_path):
    source = _local_file(tmp_path)
    route = respx.post(UPLOAD_URL).mock(return_value=httpx.Response(200, json=_created()))
    respx.get(UPLOADED_CONTENT_URL).mock(return_value=_media_redirect())

    result = upload_jira_attachment("PROJ-123", str(source), cfg=CFG)

    assert result["product"] == "jira"
    assert result["issueKey"] == "PROJ-123"
    assert result["attachmentId"] == "600100"
    assert result["filename"] == "upload.png"
    assert result["mimeType"] == "image/png"
    assert result["size"] == len(FILE_CONTENT)
    assert result["path"] == str(source)

    request = route.calls.last.request
    assert request.headers["X-Atlassian-Token"] == "no-check"
    body = request.content
    assert b'name="file"' in body
    assert b'filename="upload.png"' in body
    assert FILE_CONTENT in body


@respx.mock
def test_upload_uses_filename_override(tmp_path):
    source = _local_file(tmp_path, name="local.bin")
    route = respx.post(UPLOAD_URL).mock(return_value=httpx.Response(200, json=_created(filename="renamed.png")))
    respx.get(UPLOADED_CONTENT_URL).mock(return_value=_media_redirect())

    result = upload_jira_attachment("PROJ-123", str(source), filename="renamed.png", cfg=CFG)

    assert result["filename"] == "renamed.png"
    assert b'filename="renamed.png"' in route.calls.last.request.content


@respx.mock
def test_upload_sanitizes_filename(tmp_path):
    source = _local_file(tmp_path)
    route = respx.post(UPLOAD_URL).mock(return_value=httpx.Response(200, json=[]))

    result = upload_jira_attachment("PROJ-123", str(source), filename="../../etc/passwd", cfg=CFG)

    assert result["filename"] == "_.._etc_passwd"
    assert b'filename="_.._etc_passwd"' in route.calls.last.request.content


@respx.mock
def test_upload_falls_back_to_local_metadata_on_empty_response(tmp_path):
    source = _local_file(tmp_path)
    respx.post(UPLOAD_URL).mock(return_value=httpx.Response(200, json=[]))

    result = upload_jira_attachment("PROJ-123", str(source), cfg=CFG)

    assert result["attachmentId"] is None
    assert result["filename"] == "upload.png"
    assert result["size"] == len(FILE_CONTENT)
    assert result["attachmentUrl"] is None


def test_upload_raises_on_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        upload_jira_attachment("PROJ-123", str(tmp_path / "nope.png"), cfg=CFG)


def test_upload_raises_on_directory(tmp_path):
    with pytest.raises(ValueError, match="regular file"):
        upload_jira_attachment("PROJ-123", str(tmp_path), cfg=CFG)


@respx.mock
def test_upload_raises_on_403(tmp_path):
    source = _local_file(tmp_path)
    respx.post(UPLOAD_URL).mock(return_value=httpx.Response(403))

    with pytest.raises(RuntimeError, match="403"):
        upload_jira_attachment("PROJ-123", str(source), cfg=CFG)


@respx.mock
def test_upload_raises_on_413(tmp_path):
    source = _local_file(tmp_path)
    respx.post(UPLOAD_URL).mock(return_value=httpx.Response(413))

    with pytest.raises(RuntimeError, match="413"):
        upload_jira_attachment("PROJ-123", str(source), cfg=CFG)


@respx.mock
def test_upload_error_does_not_leak_token(tmp_path):
    source = _local_file(tmp_path)
    respx.post(UPLOAD_URL).mock(return_value=httpx.Response(401))

    with pytest.raises(RuntimeError) as exc_info:
        upload_jira_attachment("PROJ-123", str(source), cfg=CFG)

    assert "tok" not in str(exc_info.value)
    assert CFG.email not in str(exc_info.value)


@respx.mock
def test_upload_returns_media_id_and_adf_node(tmp_path):
    source = _local_file(tmp_path)
    respx.post(UPLOAD_URL).mock(return_value=httpx.Response(200, json=_created()))
    respx.get(UPLOADED_CONTENT_URL).mock(return_value=_media_redirect())

    result = upload_jira_attachment("PROJ-123", str(source), cfg=CFG)

    assert result["mediaId"] == MEDIA_ID
    assert "adfNode" not in result


@respx.mock
def test_upload_does_not_follow_media_redirect(tmp_path):
    source = _local_file(tmp_path)
    respx.post(UPLOAD_URL).mock(return_value=httpx.Response(200, json=_created()))
    content_route = respx.get(UPLOADED_CONTENT_URL).mock(return_value=_media_redirect())
    media_route = respx.get(f"https://api.media.atlassian.com/file/{MEDIA_ID}/binary").mock(
        return_value=httpx.Response(200, content=b"should not be fetched")
    )

    upload_jira_attachment("PROJ-123", str(source), cfg=CFG)

    assert content_route.called
    assert not media_route.called


@respx.mock
def test_upload_survives_unresolvable_media_id(tmp_path):
    source = _local_file(tmp_path)
    respx.post(UPLOAD_URL).mock(return_value=httpx.Response(200, json=_created()))
    respx.get(UPLOADED_CONTENT_URL).mock(return_value=httpx.Response(500))

    result = upload_jira_attachment("PROJ-123", str(source), cfg=CFG)

    assert result["attachmentId"] == UPLOADED_ID
    assert result["mediaId"] is None


@respx.mock
def test_upload_skips_media_lookup_without_attachment_id(tmp_path):
    source = _local_file(tmp_path)
    respx.post(UPLOAD_URL).mock(return_value=httpx.Response(200, json=[]))
    content_route = respx.get(UPLOADED_CONTENT_URL).mock(return_value=_media_redirect())

    result = upload_jira_attachment("PROJ-123", str(source), cfg=CFG)

    assert result["mediaId"] is None
    assert not content_route.called


@respx.mock
def test_get_attachment_reference():
    respx.get(REF_META_URL).mock(
        return_value=httpx.Response(200, json={"filename": "report.pdf", "mimeType": "application/pdf", "size": 24581})
    )
    respx.get(UPLOADED_CONTENT_URL).mock(return_value=_media_redirect())

    result = get_jira_attachment_reference(UPLOADED_ID, cfg=CFG)

    assert result["attachmentId"] == UPLOADED_ID
    assert result["filename"] == "report.pdf"
    assert result["mediaId"] == MEDIA_ID
    assert result["attachmentUrl"] == UPLOADED_CONTENT_URL
    assert "adfNode" not in result


@respx.mock
def test_get_attachment_reference_raises_on_404():
    respx.get(REF_META_URL).mock(return_value=httpx.Response(404))

    with pytest.raises(RuntimeError, match="404"):
        get_jira_attachment_reference(UPLOADED_ID, cfg=CFG)


DELETE_URL = f"{BASE}/rest/api/3/attachment/{UPLOADED_ID}"


@respx.mock
def test_deletes_jira_attachment():
    respx.get(DELETE_URL).mock(
        return_value=httpx.Response(200, json={"filename": "old.png", "mimeType": "image/png", "size": 512})
    )
    delete_route = respx.delete(DELETE_URL).mock(return_value=httpx.Response(204))

    result = delete_jira_attachment(UPLOADED_ID, cfg=CFG)

    assert result == {
        "product": "jira",
        "attachmentId": UPLOADED_ID,
        "filename": "old.png",
        "mimeType": "image/png",
        "size": 512,
        "deleted": True,
    }
    assert delete_route.called


@respx.mock
def test_delete_does_not_call_delete_when_missing():
    respx.get(DELETE_URL).mock(return_value=httpx.Response(404))
    delete_route = respx.delete(DELETE_URL).mock(return_value=httpx.Response(204))

    with pytest.raises(RuntimeError, match="404"):
        delete_jira_attachment(UPLOADED_ID, cfg=CFG)

    assert not delete_route.called


@respx.mock
def test_delete_raises_on_403():
    respx.get(DELETE_URL).mock(return_value=httpx.Response(200, json={"filename": "old.png"}))
    respx.delete(DELETE_URL).mock(return_value=httpx.Response(403))

    with pytest.raises(RuntimeError, match="403"):
        delete_jira_attachment(UPLOADED_ID, cfg=CFG)


@respx.mock
def test_delete_error_does_not_leak_token():
    respx.get(DELETE_URL).mock(return_value=httpx.Response(200, json={"filename": "old.png"}))
    respx.delete(DELETE_URL).mock(return_value=httpx.Response(401))

    with pytest.raises(RuntimeError) as exc_info:
        delete_jira_attachment(UPLOADED_ID, cfg=CFG)

    assert "tok" not in str(exc_info.value)
    assert CFG.email not in str(exc_info.value)


@respx.mock
def test_download_reports_attachment_url(tmp_path):
    respx.get(META_URL).mock(return_value=httpx.Response(200, json=_meta()))
    respx.get(CONTENT_URL).mock(return_value=httpx.Response(200, content=FILE_CONTENT))

    result = download_jira_attachment(ATTACHMENT_ID, str(tmp_path), cfg=CFG)

    # All three tools name the content URL the same way.
    assert result["attachmentUrl"] == CONTENT_URL
    assert "sourceUrl" not in result


@respx.mock
def test_reference_falls_back_to_constructed_attachment_url():
    respx.get(REF_META_URL).mock(return_value=httpx.Response(200, json={"filename": "no-content-field.png"}))
    respx.get(UPLOADED_CONTENT_URL).mock(return_value=_media_redirect())

    result = get_jira_attachment_reference(UPLOADED_ID, cfg=CFG)

    assert result["attachmentUrl"] == UPLOADED_CONTENT_URL
