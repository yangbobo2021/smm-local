"""Small contract for future agent conversation importers."""

from pathlib import Path
from typing import Any, Iterable, Protocol


class SourceAdapter(Protocol):
    name: str

    def discover(self, root: Path) -> Iterable[Path]: ...

    def normalize(self, item: dict[str, Any], byte_offset: int) -> dict[str, Any] | None: ...
