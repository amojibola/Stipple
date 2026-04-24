from abc import ABC, abstractmethod
from pathlib import Path

import aiofiles
import aiofiles.os


class FileStorageBackend(ABC):
    @abstractmethod
    async def save(self, data: bytes, relative_path: str) -> str:
        """Save file, return storage key."""

    @abstractmethod
    async def load(self, storage_key: str) -> bytes:
        """Load file by storage key."""

    @abstractmethod
    async def delete(self, storage_key: str) -> None:
        """Delete file by storage key."""

    @abstractmethod
    async def exists(self, storage_key: str) -> bool:
        """Check if file exists."""

    def resolve_path(self, storage_key: str) -> str:
        """Return absolute path for process pool workers."""
        raise NotImplementedError


class LocalDiskBackend(FileStorageBackend):
    def __init__(self, base_path: str):
        self.base = Path(base_path).resolve()

    def _safe_resolve(self, storage_key: str) -> Path:
        """Resolve path and reject anything that escapes the storage root."""
        target = (self.base / storage_key).resolve()
        try:
            target.relative_to(self.base)
        except ValueError:
            raise ValueError("Invalid storage key: path traversal detected")
        return target

    async def save(self, data: bytes, relative_path: str) -> str:
        full = self._safe_resolve(relative_path)
        full.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(full, "wb") as f:
            await f.write(data)
        return relative_path

    async def load(self, storage_key: str) -> bytes:
        full = self._safe_resolve(storage_key)
        try:
            async with aiofiles.open(full, "rb") as f:
                return await f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found in storage: {storage_key}")
        except OSError as exc:
            raise OSError(f"Failed to read file from storage: {storage_key}") from exc

    async def delete(self, storage_key: str) -> None:
        full = self._safe_resolve(storage_key)
        try:
            await aiofiles.os.remove(full)
        except FileNotFoundError:
            pass

    async def exists(self, storage_key: str) -> bool:
        full = self._safe_resolve(storage_key)
        return await aiofiles.os.path.exists(full)

    def resolve_path(self, storage_key: str) -> str:
        return str(self._safe_resolve(storage_key))
