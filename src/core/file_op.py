from pathlib import Path, PurePath
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

@dataclass
class SearchFilesError:
    error: str

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None and v != []}

@dataclass
class SearchFilesOutput:
    files: list[str]
    files_count: int
    total_files: int

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None and v != []}


class FileAccessor:
    """
    Allows a safe access to file system paths.

    Whitelist overrides blacklist and blocklist if set.
    """
    blacklist_glob: list[Path]
    whitelist_glob: list[Path]
    blocklist_prefix: list[Path]
    sensitive_suffix: list[Path]

    def __init__(self, blacklist: [str] = [], whitelist: [str] = []):
        self.blacklist_glob = []
        self.whitelist_glob = []
        for p in blacklist:
            try:
                path = Path(p)
            except RuntimeError:
                raise InvalidUserPathError(f"failed to expand '{p}'")
            self.blacklist_glob.append(path)
        for p in whitelist:
            try:
                path = Path(p)
            except RuntimeError:
                raise InvalidUserPathError(f"failed to expand '{p}'")
            self.whitelist_glob.append(path)
        
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
    
    # def search_content(
    #     self, pattern: str, path: str, file_glob: Optional[str],
    #     limit: int, offset: int, output_mode: str, context: int):
    #     if offset < 0:
    #         raise ValueError(f"offset should be non-negative, currently '{offset}'")
    #     if limit < 0:
    #         raise ValueError(f"limit should be non-negative, currently '{limit}'")
    #     """Equivalent to: grep -r pattern path"""
    #     root = Path(path).expanduser().resolve()
    #     regex = re.compile(pattern)
    #     matches = []
        
    #     # Define glob pattern
    #     glob_pattern = file_glob if file_glob else "**/*"
        
    #     # Iterate over files
    #     for file_path in root.rglob(glob_pattern):
    #         if not file_path.is_file():
    #             continue
            
    #         try:
    #             with file_path.open("r", encoding="utf-8", errors="ignore") as f:
    #                 lines = f.readlines()
                    
    #             for i, line in enumerate(lines):
    #                 if regex.search(line):
    #                     # Construct context
    #                     start = max(0, i - context)
    #                     end = min(len(lines), i + context + 1)
    #                     context_lines = "".join(lines[start:end]).strip()
                        
    #                     matches.append(f"{file_path}:{i+1}: {context_lines}")
                        
    #                     # Memory Optimization: Stop if we have enough matches
    #                     # (Only works if not needing to aggregate all before slicing)
    #                     if len(matches) > (offset + limit):
    #                         break
    #         except (PermissionError, OSError):
    #             continue
                
    #     return matches[offset : offset + limit]
        
    
    def search_files(self, pattern: str, path: str, limit: int, offset: int) -> SearchFilesOutput | SearchFilesError:
        if offset < 0:
            raise ValueError(f"offset should be non-negative, currently '{offset}'")
        if limit < 0:
            raise ValueError(f"limit should be non-negative, currently '{limit}'")
        """Equivalent to: find path -name "*pattern*" """
        
        root = FileAccessor._canonicalize_path(path)

        target_destination = (root / pattern).resolve()
        if not target_destination.is_relative_to(root):
            return SearchFilesError(
                error=f"pattern '{pattern}' needs to be relative to the root path"
            )

        stripped = pattern.strip()
        if not stripped or stripped in (".", ".."):
            return SearchFilesError(
                error=f"pattern '{pattern}' is invalid, try '*' or '**'"
            )
        if PurePath(stripped).is_absolute():
            return SearchFilesError(
                error=f"pattern '{pattern}' must be a relative pattern"
            )
        
        if "**" in stripped:
            # Recursive mode
            files_iterator = root.rglob(stripped)
        else:
            # Flat mode (only children of the root)
            files_iterator = root.glob(stripped)

        files = [str(Path(f).resolve()) for f in files_iterator if f.is_file()]
        listed_files = files[offset : offset + limit]

        return SearchFilesOutput(
            files=listed_files,
            files_count=len(listed_files),
            total_files=len(files)
        )

    def _canonicalize_path(path: str) -> Path:
        try:
            canonical_path = Path(path).expanduser().resolve()
        except RuntimeError:
            raise ValueError(f"failed to expand '{path}'")
        return canonical_path
    
    def _permission_check(self, canonical_path: Path):
        if len(self.whitelist_glob) > 0:
            for pattern in self.whitelist_glob:
                if canonical_path.match(pattern):
                    return
            raise PermissionError(f"'{canonical_path}' is not in the whitelist")
        
        for pattern in self.blacklist_glob:
            if canonical_path.match(pattern):
                raise PermissionError(f"'{canonical_path}' is blacklisted")
        
        for blocked_zone in self.blocklist_prefix:
            if canonical_path.is_relative_to(blocked_zone):
                raise PermissionError(f"'{canonical_path}' is a device path that would block or produce infinite output")
        
        for blocked_suffix in self.sensitive_suffix:
            suffix_len = len(blocked_suffix.parts)
            path_tail = canonical_path.parts[-suffix_len:]
            if path_tail == blocked_suffix.parts:
                raise PermissionError(f"'{canonical_path}' is a sensitive file")
        
        if self._is_blocked_device_path(canonical_path):
            raise PermissionError(f"'{canonical_path}' is a device path that would block or produce infinite output")

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