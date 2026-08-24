from __future__ import annotations

import json
from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from .config import get_config
from .jira import delete_jira_attachment as _delete_jira_attachment
from .jira import download_jira_attachment as _download_jira_attachment
from .jira import get_jira_attachment_reference as _get_jira_attachment_reference
from .jira import upload_jira_attachment as _upload_jira_attachment

mcp = MCPServer("Atlassian Attachments")


@mcp.tool(
    # Writes a file into output_dir, so not read-only. Destructive because the
    # caller names the path: overwrite=true replaces whatever is already there,
    # and a size mismatch unlinks the target. Idempotent all the same — repeated
    # calls with the same arguments converge on the same file.
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=True,
        idempotent_hint=True,
        open_world_hint=True,
    ),
)
def download_jira_attachment(
    attachment_id: Annotated[
        str,
        Field(description="Jira attachment ID, for example 439535."),
    ],
    output_dir: Annotated[
        str,
        Field(description="Local directory to save the file. Created automatically if it does not exist."),
    ],
    filename: Annotated[
        str | None,
        Field(description="Uses Jira metadata filename when omitted."),
    ] = None,
    overwrite: Annotated[
        bool,
        Field(description="Replace an existing file when true. Fail if the file exists when false."),
    ] = False,
) -> str:
    """[Atlassian] Download Jira attachment by ID to a local directory."""
    cfg = get_config()
    result = _download_jira_attachment(
        attachment_id=attachment_id,
        output_dir=output_dir,
        filename=filename,
        overwrite=overwrite,
        cfg=cfg,
    )
    return json.dumps(result, indent=2)


@mcp.tool(
    # Creates a new attachment on the issue: not read-only, and not idempotent
    # because Jira adds another attachment on every call rather than replacing
    # the previous one. Nothing existing is removed, so not destructive.
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=True,
    ),
)
def upload_jira_attachment(
    issue_key: Annotated[
        str,
        Field(description="Jira issue key or ID, for example PROJ-123."),
    ],
    file_path: Annotated[
        str,
        Field(description="Path to the local file to upload. Must exist."),
    ],
    filename: Annotated[
        str | None,
        Field(description="Name to store in Jira. Uses the local filename when omitted."),
    ] = None,
) -> str:
    """[Atlassian] Upload local file as Jira attachment.

    Returns mediaId, the Media Services UUID needed to embed the file in an issue
    description or comment via a Jira content tool. An ADF media node references
    this UUID, never attachmentId:
    {"type":"media","attrs":{"type":"file","id":<mediaId>,"collection":"","alt":<filename>}}
    Wrap it in mediaSingle (image), mediaGroup (file card), or mediaInline (chip);
    a bare media node does not render. mediaId is null if it cannot be resolved.
    """
    cfg = get_config()
    result = _upload_jira_attachment(
        issue_key=issue_key,
        file_path=file_path,
        filename=filename,
        cfg=cfg,
    )
    return json.dumps(result, indent=2)


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=True,
        open_world_hint=True,
    ),
)
def get_jira_attachment_reference(
    attachment_id: Annotated[
        str,
        Field(description="Jira attachment ID, for example 439535."),
    ],
) -> str:
    """[Atlassian] Resolve Jira attachment ID into its ADF media UUID.

    For an attachment already on an issue; after an upload use the mediaId that
    upload_jira_attachment already returned instead of calling this. See that
    tool for the ADF media node shape.
    """
    cfg = get_config()
    result = _get_jira_attachment_reference(attachment_id=attachment_id, cfg=cfg)
    return json.dumps(result, indent=2)


@mcp.tool(
    # Removes the attachment from the issue. Jira offers no undo, so this is
    # destructive; idempotent_hint is omitted because a repeat call 404s rather
    # than converging.
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=True,
        open_world_hint=True,
    ),
)
def delete_jira_attachment(
    attachment_id: Annotated[
        str,
        Field(description="Jira attachment ID to delete permanently."),
    ],
) -> str:
    """[Atlassian] Delete Jira attachment by ID. Permanent, with no undo."""
    cfg = get_config()
    result = _delete_jira_attachment(attachment_id=attachment_id, cfg=cfg)
    return json.dumps(result, indent=2)


def main() -> None:
    mcp.run(transport="stdio")
