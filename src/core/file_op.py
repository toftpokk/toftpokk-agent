from pathlib import Path
import os
import json
from dataclasses import dataclass
import errno

MAX_READ_CHARS = 100_000

@dataclass
class WriteError:
    error: str

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None and v != []}

@dataclass
class WriteOutput:
    bytes_written: int
    dirs_created: bool

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None and v != []}


@dataclass
class ReadError:
    error: str

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None and v != []}

@dataclass
class ReadOutput:
    content: str
    lines_count: int
    total_lines: int
    total_file_size: int

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None and v != []}


class FileAccessor:
    """
    Allows a safe access to file system paths.

    Whitelist overrides blacklist and blocklist if set.
    """
    blacklist_prefix: list[Path]
    whitelist_prefix: list[Path]
    blocklist_prefix: list[Path]
    sensitive_suffix: list[Path]

    def __init__(self, blacklist: [str] = [], whitelist: [str] = []):
        self.blacklist_prefix = []
        self.whitelist_prefix = []
        for p in blacklist:
            try:
                path = Path(p)
            except RuntimeError:
                raise InvalidUserPathError(f"failed to expand '{p}'")
            self.blacklist_prefix.append(path)
        for p in whitelist:
            try:
                path = Path(p)
            except RuntimeError:
                raise InvalidUserPathError(f"failed to expand '{p}'")
            self.whitelist_prefix.append(path)
        
        self.blocklist_prefix = []
        blocklist_prefix = [
            # Infinite output
            "/dev/zero", "/dev/random", "/dev/urandom", "/dev/full",
            # Blocks
            "/dev/stdin", "/dev/tty", "/dev/console",
            # Nonsensical to read
            "/dev/stdout", "/dev/stderr",
            # File descriptors
            "/dev/fd/0", "/dev/fd/1", "/dev/fd/2"
        ]
        for p in blocklist_prefix:
            try:
                path = Path(p)
            except RuntimeError:
                raise InvalidUserPathError(f"failed to expand '{p}'")
            self.blocklist_prefix.append(path)

        # originally used for files under hermes config. Now it's for all files
        self.sensitive_suffix = []
        sensitive_suffix = [
            "auth.json",
            "auth.lock",
            ".anthropic_oauth.json",
            ".env",
            "webhook_subscriptions.json",
            "auth/google_oauth.json",
            "cache/bws_cache.json"
        ]
        for p in sensitive_suffix:
            try:
                path = Path(p)
            except RuntimeError:
                raise InvalidUserPathError(f"failed to expand '{p}'")
            self.sensitive_suffix.append(path)

    def read_file(self, path_input: str, offset: int, limit: int) -> ReadOutput | ReadError:
        if offset < 0:
            raise ValueError(f"offset should be non-negative, currently '{offset}'")
        if limit < 0:
            raise ValueError(f"limit should be non-negative, currently '{limit}'")
        
        canonical_path = FileAccessor._canonicalize_path(path_input)

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

    def write_file(self, path_input: str, content: str) -> WriteOutput | WriteError:
        canonical_path = FileAccessor._canonicalize_path(path_input)
        parent = os.path.dirname(canonical_path)

        try:
            self._permission_check(canonical_path)
        except PermissionError as error:
            return ReadError(
                error=f"permission error: {error}"
            )

        dirs_created = False
        try:
            os.makedirs(parent)
            dirs_created = True
        except FileExistsError:
            pass

        bytes_written = 0
        try: 
            with open(canonical_path, 'w') as f:
                bytes_written = f.write(content)
        except NotADirectoryError:
            return WriteError(
                error=f"one parent directory of '{canonical_path}' is a file"
            )
        except IsADirectoryError:
            return WriteError(
                error=f"'{canonical_path}' is a directory"
            )
        except PermissionError:
            return WriteError(
                error=f"permission error: file '{canonical_path}' could not be written to"
            )
        except OSError as e:
            if e.errno == errno.ENOSPC:
                return WriteError(
                error=f"no space left on device"
            )
            raise

        return WriteOutput(
            bytes_written=bytes_written,
            dirs_created=dirs_created,
        )


    def _canonicalize_path(path: str) -> Path:
        try:
            canonical_path = Path(path).expanduser().resolve()
        except RuntimeError:
            raise ValueError(f"failed to expand '{path}'")
        return canonical_path
    
    def _permission_check(self, canonical_path: Path):
        if len(self.whitelist_prefix) > 0:
            for allowed_zone in self.whitelist_prefix:
                if canonical_path.is_relative_to(allowed_zone):
                    return
            raise PermissionError(f"'{canonical_path}' is not in the whitelist")
        
        for blocked_zone in self.blacklist_prefix:
            if canonical_path.is_relative_to(blocked_zone):
                raise PermissionError(f"'{canonical_path}' is blacklisted")
        
        for blocked_zone in self.blocklist_prefix:
            if canonical_path.is_relative_to(blocked_zone):
                raise PermissionError(f"'{canonical_path}' is a device file that would block or produce infinite output")
        
        for blocked_suffix in self.sensitive_suffix:
            suffix_len = len(blocked_suffix.parts)
            path_tail = canonical_path.parts[-suffix_len:]
            if path_tail == blocked_suffix.parts:
                raise PermissionError(f"'{canonical_path}' is a sensitive file")
        
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