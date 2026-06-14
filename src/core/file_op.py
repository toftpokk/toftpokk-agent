from pathlib import Path
import os
import json
from dataclasses import dataclass

MAX_READ_CHARS = 100_000

@dataclass
class ReadError:
    error: str

    def to_dict(self) -> dict:
        return {
            "error": self.error
        }

@dataclass
class ReadOutput:
    content: str
    lines_count: int
    total_lines: int
    total_file_size: int
    hint: str = None

    def set_hint(self, hint: str):
        self.hint = hint

    def to_dict(self) -> dict:
        output = {
            "content": self.content,
            "lines_count": self.lines_count,
            "total_lines": self.total_lines,
            "total_file_size": self.total_file_size,
        }
        if not self.hint is None:
            output["hint"] = self.hint
        return output


class FileAccessor:
    """
    Allows a safe access to file system paths.

    Whitelist overrides blacklist and blocklist if set.
    """
    blacklist: list[Path]
    whitelist: list[Path]
    blocklist: list[Path]

    def __init__(self, blacklist: [str], whitelist: [str]):
        self.blacklist = []
        self.whitelist = []
        for p in blacklist:
            try:
                path = Path(p).expanduser().resolve()
            except RuntimeError:
                raise InvalidUserPathError(f"failed to expand '{p}'")
            self.blacklist.append(path)
        for p in whitelist:
            try:
                path = Path(p).expanduser().resolve()
            except RuntimeError:
                raise InvalidUserPathError(f"failed to expand '{p}'")
            self.whitelist.append(path)
        
        self.blocklist = []
        blocklist = [
            # Infinite output
            "/dev/zero", "/dev/random", "/dev/urandom", "/dev/full",
            # Blocks
            "/dev/stdin", "/dev/tty", "/dev/console",
            # Nonsensical to read
            "/dev/stdout", "/dev/stderr",
            # File descriptors
            "/dev/fd/0", "/dev/fd/1", "/dev/fd/2"
        ]
        for p in blocklist:
            try:
                path = Path(p).expanduser().resolve()
            except RuntimeError:
                raise InvalidUserPathError(f"failed to expand '{p}'")
            self.blocklist.append(path)

    def read_file(self, path: str, offset: int, limit: int) -> ReadOutput | ReadError:
        if offset < 0:
            raise ValueError(f"offset should be non-negative, currently '{offset}'")
        if limit < 0:
            raise ValueError(f"limit should be non-negative, currently '{limit}'")
        try:
            canonical_path = Path(path).expanduser().resolve()
        except RuntimeError:
            raise ValueError(f"failed to expand '{path}'")

        try:
            self._permission_check(canonical_path)
        except PermissionError as error:
            return ReadError(
                error=f"permission error: {error}"
            )

        buf = []
        lines_count = 0
        total_lines = 0
        total_file_size = 0
        try:
            with open(canonical_path, "r") as f:
                fd = f.fileno()
                total_file_size = os.fstat(fd).st_size

                if self._is_binary(fd):
                    return ReadError(
                        error=f"file '{canonical_path}' is binary"
                    )
               
                for line in f:
                    lines_count += 1
                    buf.append(line)

                    if lines_count >= limit:
                        break
                
                # Ref: https://stackoverflow.com/questions/845058/how-to-get-the-line-count-of-a-large-file-cheaply-in-python
                f.seek(0)
                total_lines = sum(1 for _ in f)
        except PermissionError:
            return ReadError(
                error=f"permission error: file '{canonical_path}' could not be read"
            )
        except FileNotFoundError:
            return ReadError(
                error=f"file '{canonical_path}' is does not exist"
            )
        except IsADirectoryError:
            return ReadError(
                error=f"path '{canonical_path}' is a directory"
            )

        return ReadOutput(
            content="".join(buf),
            lines_count=lines_count,
            total_lines=total_lines,
            total_file_size=total_file_size,
        )
    
    # TODO similar file scoring like hermes
    # def simiar_files(self, path: str) -> [str]:
    #     try:
    #         canonical_path = Path(path).expanduser().resolve()
    #     except RuntimeError:
    #         raise InvalidUserPathError(f"failed to expand '{path}'")
        
    
    def _permission_check(self, canonical_path: Path):
        if len(self.whitelist) > 0:
            for allowed_zone in self.whitelist:
                if canonical_path.is_relative_to(allowed_zone):
                    return
            raise PermissionError(f"'{canonical_path}' is not in the whitelist")
        
        for blocked_zone in self.blacklist:
            if canonical_path.is_relative_to(blocked_zone):
                raise PermissionError(f"'{canonical_path}' is blacklisted")
        
        for blocked_zone in self.blocklist:
            if canonical_path.is_relative_to(blocked_zone):
                raise PermissionError(f"'{canonical_path}' is a device file that would block or produce infinite output")
        
        if self._is_blocked_device_path(canonical_path):
            raise PermissionError(f"'{canonical_path}' is a device file that would block or produce infinite output")

    def _is_blocked_device_path(self, canonical_path: Path) -> bool:
        path_str = str(canonical_path)
        # stdio
        if path_str.startswith("/proc/") and path_str.endswith(("/fd/0", "/fd/1", "/fd/2")):
            return True
        # secret leaking, copied from hermes
        if path_str.startswith("/proc/") and path_str.endswith(("/environ", "/cmdline", "/maps")):
            return True
        return False

    def _is_binary(self, fd: int) -> bool:
        block_size = 1024
        try:
            initial_bytes = os.read(fd, block_size)
            os.lseek(fd, 0, os.SEEK_SET)
        except OSError:
            # cannot read -> assumed binart
            return True
        
        if not initial_bytes:
            # empty file
            return False
        
        if b"\x00" in initial_bytes:
            return True
        
        return False