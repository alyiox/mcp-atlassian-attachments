from __future__ import annotations

import json
from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from .config import get_config
from .jira import download_jira_attachment as _download_jira_attachment

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


def main() -> None:
    mcp.run(transport="stdio")
