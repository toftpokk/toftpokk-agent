from dataclasses import dataclass
from typing import Annotated, Callable, ParamSpec, TypeVar, Optional
import os
import json

from pydantic import Field

from core.core import tool
from core import file_op

P = ParamSpec("P")
R = TypeVar("R")

FOREGROUND_MAX_TIMEOUT=600
# From hermes file_tools.py, vision_tools.py, terminal_tool.py,

# REGISTRY: dict[str, Callable[P,R]] = {}
    
# def load(name: str) -> Callable[P,R]:
#     return REGISTRY.get(name)

# def list_all() -> dict[str, Callable[P,R]]:
#     return REGISTRY

# def _registered(func: Callable[P,R]):
#     REGISTRY[func.tool_definition["name"]] = func
#     return func
    

@dataclass
class ToolError:
    error: str

    def to_dict(self):
        return {
            "error": self.error
        }

def make_tools(file_accessor: file_op.FileAccessor) -> dict[str,Callable[P,R]]:
    @tool
    def read_file(
        path: Annotated[str, Field(
            description="Path to the file to read (absolute, relative, or ~/path)",
        )],
        offset: Annotated[int, Field(
            description="Line number to start reading from (1-indexed, default: 1)",
            ge=1,
        )] = 1,
        limit: Annotated[int, Field(
            description="Maximum number of lines to read (default: 500, max: 2000)",
            le=2000,
        )] = 500,
    ) -> str:
        """Read a text file with line numbers and pagination. Use this instead of cat/head/tail in terminal. 
        Output format: 'LINE_NUM|CONTENT'. Suggests similar filenames if not found. Use offset and limit for large files. 
        Reads exceeding ~100K characters are rejected; use offset and limit to read specific sections of large files. 
        
        NOTE: Cannot read images or binary files
        """
        # — use vision_analyze for images.
        # TODO
        offset = int(offset)
        limit = int(limit)

        # normalize
        if offset < 0:
            offset = 0
        if limit < 0:
            limit = 0
        elif limit > 2000:
            limit = 2000
        
        read_result = file_accessor.read_file(path, offset, limit)
        return json.dumps(read_result.to_dict())

    @tool
    def write_file(
        path: Annotated[str, Field(
            description="Path to the file to write (will be created if it doesn't exist, overwritten if it does)",
        )],
        content: Annotated[str, Field(
            description="Complete content to write to the file",
        )],
    ):
        """
        Write content to a file, completely replacing existing content. Use this instead of echo/cat heredoc in terminal. 
        Creates parent directories automatically. OVERWRITES the entire file — use 'patch' for targeted edits. 
        Auto-runs syntax checks on .py/.json/.yaml/.toml and other linted languages; only NEW errors introduced by this write are surfaced (pre-existing errors are filtered out).
        """
        
        read_result = file_accessor.write_file(path, content)
        return json.dumps(read_result.to_dict())

    @tool
    def search_files(
        pattern: Annotated[
            str, 
            Field(description="Glob pattern (e.g., '*.py')")
        ],
        path: Annotated[
            str, 
            Field(default=".", description="Directory or file to search in (default: current working directory)")
        ] = ".",
        limit: Annotated[
            int, 
            Field(default=50, description="Maximum number of results to return (default: 50)")
        ] = 50,
        offset: Annotated[
            int, 
            Field(default=0, description="Skip first N results for pagination (default: 0)")
        ] = 0,
    ):
        offset = int(offset)
        limit = int(limit)

        # normalize
        if offset < 0:
            offset = 0
        if limit < 0:
            limit = 0

        read_result = file_accessor.search_files(pattern, path, limit, offset)
        return json.dumps(read_result.to_dict())
    
    @tool
    def search_content(
        pattern: Annotated[
            str, 
            Field(description="Regex pattern (e.g., 'file.*')")
        ],
        path: Annotated[
            str, 
            Field(default=".", description="Directory or file to search in (default: current working directory)")
        ] = ".",
        file_glob: Annotated[
            Optional[str], 
            Field(default=None, description="Filter files by pattern in grep mode (e.g., '*.py' to only search Python files)")
        ] = None,
        limit: Annotated[
            int, 
            Field(default=50, description="Maximum number of results to return (default: 50)")
        ] = 50,
        offset: Annotated[
            int, 
            Field(default=0, description="Skip first N results for pagination (default: 0)")
        ] = 0,
        context: Annotated[
            int, 
            Field(default=0, description="Number of context lines before and after each match (default: 0)")
        ] = 0,
    ):
        offset = int(offset)
        limit = int(limit)

        # normalize
        if offset < 0:
            offset = 0
        if limit < 0:
            limit = 0
        
        if file_glob is None:
            file_glob = '*'

        read_result = file_accessor.search_content(pattern, path, file_glob, limit, offset, context)
        return json.dumps(read_result.to_dict())

    return {
        "read_file": read_file,
        "write_file": write_file,
        "search_files": search_files,
        "search_content": search_content,
    }

# @tool
# def search_files(
#     pattern: Annotated[
#         str, 
#         Field(description="Regex pattern for content search, or glob pattern (e.g., '*.py') for file search")
#     ],
#     target: Annotated[
#         Literal["content", "files"], 
#         Field(default="content", description="'content' searches inside file contents, 'files' searches for files by name")
#     ] = "content",
#     path: Annotated[
#         str, 
#         Field(default=".", description="Directory or file to search in (default: current working directory)")
#     ] = ".",
#     file_glob: Annotated[
#         Optional[str], 
#         Field(default=None, description="Filter files by pattern in grep mode (e.g., '*.py' to only search Python files)")
#     ] = None,
#     limit: Annotated[
#         int, 
#         Field(default=50, description="Maximum number of results to return (default: 50)")
#     ] = 50,
#     offset: Annotated[
#         int, 
#         Field(default=0, description="Skip first N results for pagination (default: 0)")
#     ] = 0,
#     output_mode: Annotated[
#         Literal["content", "files_only", "count"], 
#         Field(default="content", description="Output format for grep mode: 'content' shows matching lines with line numbers, 'files_only' lists file paths, 'count' shows match counts per file")
#     ] = "content",
#     context: Annotated[
#         int, 
#         Field(default=0, description="Number of context lines before and after each match (grep mode only)")
#     ] = 0,
# ):
#     """
#     Search file contents or find files by name. Use this instead of grep/rg/find/ls in terminal. Ripgrep-backed, faster than shell equivalents.
#     Content search (target='content'): Regex search inside files. Output modes: full matches with line numbers, file paths only, or match counts.
#     File search (target='files'): Find files by glob pattern (e.g., '*.py', '*config*'). Also use this instead of ls — results sorted by modification time.
#     """
#     # TODO
#     pass

# @tool
# def patch(
#     mode: Annotated[Literal["replace", "patch"], 
#         Field(default="replace", description="Edit mode. 'replace' (default): requires path + old_string + new_string. 'patch': requires patch content only.")] = "replace",
#     path: Annotated[Optional[str], 
#         Field(default=None, description="REQUIRED when mode='replace'. File path to edit.")] = None,
#     old_string: Annotated[Optional[str], 
#         Field(default=None, description="REQUIRED when mode='replace'. Exact text to find and replace. Must be unique in the file unless replace_all=true. Include surrounding context lines to ensure uniqueness.")] = None,
#     new_string: Annotated[Optional[str], 
#         Field(default=None, description="REQUIRED when mode='replace'. Replacement text. Pass empty string '' to delete the matched text.")] = None,
#     replace_all: Annotated[bool, 
#         Field(default=False, description="Replace all occurrences instead of requiring a unique match (default: false)")] = False,
#     patch: Annotated[Optional[str], 
#         Field(default=None, description="REQUIRED when mode='patch'. V4A format patch content. Format:\n*** Begin Patch\n*** Update File: path/to/file\n@@ context hint @@\n context line\n-removed line\n+added line\n*** End Patch")] = None,
#     cross_profile: Annotated[bool, 
#         Field(default=False, description="Opt out of the cross-profile soft guard. Defaults to false. Set true ONLY after explicit user direction to edit another Hermes profile's skills/plugins/cron/memories.")] = False,
# ):
#     """
#     Targeted find-and-replace edits in files. Use this instead of sed/awk in terminal. Uses fuzzy matching (9 strategies) so minor whitespace/indentation differences won't break it.
#     Returns a unified diff. Auto-runs syntax checks after editing.
    
#     REPLACE MODE (mode='replace', default): find a unique string and replace it. REQUIRED PARAMETERS: mode, path, old_string, new_string.
#     PATCH MODE (mode='patch'): apply V4A multi-file patches for bulk changes. REQUIRED PARAMETERS: mode, patch.
#     """
#     # TODO
#     pass


# @tool(dependencies=[
#     read_file.tool_definition.name,
#     search_files.tool_definition.name,
#     patch.tool_definition.name,
#     write_file.tool_definition.name,
# ])
# def terminal(
#     command: Annotated[str, Field(
#         description="The command to execute on the VM"
#     )],
# ):
#     """Execute shell commands on a Linux environment. Filesystem usually persists between calls.

#     Do NOT use cat/head/tail to read files — use read_file instead.
#     Do NOT use grep/rg/find to search — use search_files instead.
#     Do NOT use ls to list directories — use search_files(target='files') instead.
#     Do NOT use sed/awk to edit files — use patch instead.
#     Do NOT use echo/cat heredoc to create files — use write_file instead.

#     Reserve terminal for: builds, installs, git, processes, scripts, network, package managers, and anything that needs a shell.
#     """

#     # Foreground (default): Commands return INSTANTLY when done, even if the timeout is high. Set timeout=300 for long builds/scripts — you'll still get the result in seconds if it's fast. Prefer foreground for short commands.
#     # Background: Set background=true to get a session_id. Almost always pair with notify_on_complete=true — bg without notify runs SILENTLY and you have no way to learn it finished short of calling process(action='poll') yourself. Two legitimate uses:
#     # (1) Long-lived processes that never exit (servers, watchers, daemons) — silent is correct, there's no exit to notify on.
#     # (2) Long-running bounded tasks (tests, builds, deploys, CI pollers, batch jobs) — MUST set notify_on_complete=true. Without it you'll either forget to poll or sit blocked waiting for the user to surface the result.
#     # For servers/watchers, do NOT use shell-level background wrappers (nohup/disown/setsid/trailing '&') in foreground mode. Use background=true so Hermes can track lifecycle and output.
#     # After starting a server, verify readiness with a health check or log signal, then run tests in a separate terminal() call. Avoid blind sleep loops.
#     # Use process(action="poll") for progress checks, process(action="wait") to block until done.
#     # Working directory: Use 'workdir' for per-command cwd.
#     # PTY mode: Set pty=true for interactive CLI tools (Codex, Claude Code, Python REPL).

#     # Do NOT use vim/nano/interactive tools without pty=true — they hang without a pseudo-terminal. Pipe git output to cat if it might page.
#     # """
#     # TODO
#     pass
