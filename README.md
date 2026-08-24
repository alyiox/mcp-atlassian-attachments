# MCP Atlassian Attachments

[![CI](https://github.com/alyiox/mcp-atlassian-attachments/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/alyiox/mcp-atlassian-attachments/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/mcp-atlassian-attachments.svg)](https://pypi.org/project/mcp-atlassian-attachments/)
[![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

<!-- mcp-name: io.github.alyiox/mcp-atlassian-attachments -->

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server for downloading Jira Cloud attachments by attachment ID to local disk, and uploading local files as attachments to a Jira issue.

> **Supplement to the official Atlassian MCP server.**
> The [official Atlassian MCP server](https://mcp.atlassian.com/v1/mcp) covers search, issue management, and content operations but does not move attachment files between Jira and local disk. This server fills that gap.

**Requirements:** Python 3.13+, an Atlassian Cloud account, and an API token with at least the `read:jira-work` scope. Uploading also needs `write:jira-work`.

## Authentication

Scoped tokens are recommended to limit access to exactly the permissions needed.

> **Note:** The granular `read:attachment:jira` scope is not sufficient — Jira's attachment metadata endpoint (`/rest/api/3/attachment/{id}`) requires `read:jira-work` to resolve issue-level permissions. A classic (unscoped) API token also works.

### Create an API token

1. Go to [id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Click **Create API token**
3. Choose **"Create API token with scopes"** and select `read:jira-work` (add `write:jira-work` to upload), **or** choose **"Classic API token"** for full access
4. Copy the generated token

## Quick start

The fastest way to try the server is with the [MCP Inspector](https://github.com/modelcontextprotocol/inspector). Set the three required environment variables and run:

**From the published package** (no clone needed):

```bash
ATLASSIAN_SITE_URL=https://yourorg.atlassian.net \
ATLASSIAN_EMAIL=your.email@example.com \
ATLASSIAN_API_TOKEN=your-api-token \
npx -y @modelcontextprotocol/inspector uvx mcp-atlassian-attachments
```

**From a local clone:**

```bash
ATLASSIAN_SITE_URL=https://yourorg.atlassian.net \
ATLASSIAN_EMAIL=your.email@example.com \
ATLASSIAN_API_TOKEN=your-api-token \
npx -y @modelcontextprotocol/inspector uv run mcp-atlassian-attachments
```

## Configuration

Set environment variables or create a config file. Environment variables take priority.

**Environment variables:**

```bash
export ATLASSIAN_SITE_URL="https://yourorg.atlassian.net"
export ATLASSIAN_EMAIL="your.email@example.com"
export ATLASSIAN_API_TOKEN="your-api-token"
```

**Config file** (`~/.config/mcp-atlassian-attachments/config.json`):

```json
{
  "site_url": "https://yourorg.atlassian.net",
  "email": "your.email@example.com",
  "api_token": "your-api-token"
}
```

## Tools

| Tool | Description | Required params |
|------|-------------|-----------------|
| **`download_jira_attachment`** | Download a Jira attachment by ID. | `attachment_id`, `output_dir` |
| **`upload_jira_attachment`** | Upload a local file as an attachment on a Jira issue. | `issue_key`, `file_path` |
| **`get_jira_attachment_reference`** | Resolve an existing attachment into an ADF media node. | `attachment_id` |
| **`delete_jira_attachment`** | Permanently delete an attachment by ID. | `attachment_id` |

### `download_jira_attachment`

| Parameter | Type | Description |
|-----------|------|-------------|
| `attachment_id` | string | Jira attachment ID |
| `output_dir` | string | Local directory for the saved file. Created automatically if it does not exist. |
| `filename` | string (optional) | Override filename. Uses metadata filename when omitted. |
| `overwrite` | bool (optional) | Replace an existing file. Defaults to `false`. |

Returns:

```json
{
  "product": "jira",
  "attachmentId": "439535",
  "filename": "screenshot.png",
  "mimeType": "image/png",
  "size": 496724,
  "path": "/your/output/dir/screenshot.png",
  "attachmentUrl": "https://yourorg.atlassian.net/rest/api/3/attachment/content/439535"
}
```

### `upload_jira_attachment`

| Parameter | Type | Description |
|-----------|------|-------------|
| `issue_key` | string | Jira issue key or ID, for example `PROJ-123` |
| `file_path` | string | Path to the local file to upload. Must exist. |
| `filename` | string (optional) | Name to store in Jira. Uses the local filename when omitted. |

Returns:

```json
{
  "product": "jira",
  "issueKey": "PROJ-123",
  "attachmentId": "600100",
  "filename": "report.png",
  "mimeType": "image/png",
  "size": 24581,
  "path": "/your/local/dir/report.png",
  "attachmentUrl": "https://yourorg.atlassian.net/rest/api/3/attachment/content/600100",
  "mediaId": "6df94659-caa7-4561-bbe3-6384ec534bba"
}
```

Each call adds a new attachment; Jira does not replace a same-named file. Uploads larger than the site attachment size limit fail with a `413`.

### `get_jira_attachment_reference`

| Parameter | Type | Description |
|-----------|------|-------------|
| `attachment_id` | string | Jira attachment ID |

Read-only. Returns `mediaId` for an attachment that is **already** on an issue:

```json
{
  "product": "jira",
  "attachmentId": "439535",
  "filename": "screenshot.png",
  "mimeType": "image/png",
  "size": 496724,
  "attachmentUrl": "https://yourorg.atlassian.net/rest/api/3/attachment/content/439535",
  "mediaId": "6df94659-caa7-4561-bbe3-6384ec534bba"
}
```

After an upload you do **not** need this tool — `upload_jira_attachment` already returns `mediaId`, so embedding costs no extra call.

### `delete_jira_attachment`

| Parameter | Type | Description |
|-----------|------|-------------|
| `attachment_id` | string | Jira attachment ID to delete permanently |

Needs `write:jira-work`. Metadata is read before the delete, so the result reports what was removed and a missing ID fails without attempting anything:

```json
{
  "product": "jira",
  "attachmentId": "481718",
  "filename": "delete-me.txt",
  "mimeType": "text/plain",
  "size": 31,
  "deleted": true
}
```

> **There is no undo.** Jira deletes the file outright, and a second call to the same ID fails with `404`.
>
> **Deleting does not clean up references.** If the attachment was embedded in a description or comment, the ADF media node stays exactly where it was and becomes a dangling reference — verified against a live issue. Remove the node yourself if you delete a file that was referenced.

## Referencing an attachment in a description or comment

Uploading a file attaches it, but nothing appears inline in the description or a comment. Rendering it requires an [ADF](https://developer.atlassian.com/cloud/jira/platform/apis/document/structure/) media node — and that node identifies the file by its **Media Services UUID**, not by the numeric attachment ID:

```json
{
  "type": "mediaSingle",
  "attrs": { "layout": "center" },
  "content": [
    {
      "type": "media",
      "attrs": {
        "type": "file",
        "id": "6df94659-caa7-4561-bbe3-6384ec534bba",
        "collection": "",
        "alt": "report.png"
      }
    }
  ]
}
```

No Jira attachment metadata endpoint exposes that UUID, which is why this server resolves it: `GET /rest/api/3/attachment/content/{id}` answers with a `303` to `https://api.media.atlassian.com/file/{mediaId}/binary`, so reading the `Location` header without following the redirect yields the UUID at no download cost. The UUID exists as soon as the file is attached — it does not depend on the attachment being referenced anywhere.

Both tools therefore return `mediaId`. Writing the node into the issue is deliberately left to a Jira content tool such as the official Atlassian MCP server, whose `addCommentToJiraIssue` and `editJiraIssue` accept `contentFormat: "adf"` — this server moves files and does not edit issue content:

1. `upload_jira_attachment` → take `mediaId` from the result
2. Post a comment with an ADF body wrapping a media node built from it:

```json
{
  "version": 1,
  "type": "doc",
  "content": [
    { "type": "paragraph", "content": [{ "type": "text", "text": "Latest run:" }] },
    { "type": "mediaSingle", "attrs": { "layout": "center" }, "content": [ "...the media node..." ] }
  ]
}
```

For a description, read the existing ADF, append the node, and write the whole document back — `PUT /rest/api/3/issue/{key}` replaces the field rather than appending to it.

Notes:

- A bare `media` node is not rendered; it must be wrapped in `mediaSingle` (single file), `mediaGroup` (file-card list), or `mediaInline` (inline chip).
- `collection` is `""` for Jira issue attachments.
- Optional `width`/`height` on the media node set the intrinsic pixel size, and are only honoured inside `mediaSingle`.
- `mediaId` is best-effort: if the redirect cannot be read it comes back `null`, and the upload itself still succeeds.

### Simpler alternative: v2 wiki markup

The older v2 endpoints still accept wiki markup and convert it to ADF server-side, resolving the attachment **by filename** — so no media UUID is needed:

```bash
POST /rest/api/2/issue/PROJ-123/comment
{ "body": "See attached: !report.png|thumbnail!" }
```

Jira stores that as a proper `media` node with the correct UUID filled in. Confirmed working on Jira Cloud as of August 2026.

Two behaviours to know about, both verified against a live issue:

- **Dimensions are a fixed placeholder, not the real ones.** The conversion always writes `width: 200, height: 183` regardless of the image — a 64x48 and an 8x8 PNG both came back as 200x183. `!file|width=300!` sets the width but leaves height at 183, so the aspect ratio is wrong unless you write the ADF yourself.
- **Duplicate filenames resolve to the oldest.** With two attachments both named `ambiguous.png`, `!ambiguous.png!` resolved to the *first* one uploaded. Re-uploading under the same name to "update" an image will keep showing the old file.

Prefer `mediaId` when you want to be explicit: it is unambiguous with duplicate names, it lets you set true dimensions, it works with v3/ADF (which is what the official Atlassian MCP server writes), and it does not depend on a legacy path Atlassian may eventually retire.

## MCP host configuration

Add the following to your MCP host's config file. The JSON is the same for Cursor (`.cursor/mcp.json`), Claude Desktop (`claude_desktop_config.json`), and Claude Code (`.claude.json`).

```json
{
  "mcpServers": {
    "atlassian": {
      "command": "uvx",
      "args": ["mcp-atlassian-attachments"],
      "env": {
        "ATLASSIAN_SITE_URL": "https://yourorg.atlassian.net",
        "ATLASSIAN_EMAIL": "your.email@example.com",
        "ATLASSIAN_API_TOKEN": "your-api-token"
      }
    }
  }
}
```

## Security

- `ATLASSIAN_API_TOKEN` is never logged or included in error messages.
- The computed `Authorization` header is never exposed in tool output or errors.
- File writes are confined to the provided `output_dir`.
- Filenames are sanitized to prevent path traversal, both on download and on the name sent to Jira.
- Uploads read exactly the file at `file_path` and send nothing else.

## Tests

```bash
uv run pytest tests/ -v
```

## Roadmap

- **`download_confluence_attachment_tool`** — Confluence Cloud uses a different API (`/wiki/api/v2/`) and a different identifier model. Planned for a future release.

## License

MIT. See [LICENSE](LICENSE).
