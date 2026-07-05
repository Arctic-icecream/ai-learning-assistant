from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4


@dataclass(frozen=True)
class StagedFileDeletion:
    original_path: Path
    staged_path: Path

    def finalize(self) -> None:
        self.staged_path.unlink(missing_ok=True)

    def restore(self) -> None:
        if not self.staged_path.exists():
            return
        if self.original_path.exists():
            raise FileExistsError("Cannot restore file because its original path exists")
        self.staged_path.replace(self.original_path)


def stage_uploaded_file(
    storage_path: Path, upload_directory: Path
) -> StagedFileDeletion | None:
    upload_root = upload_directory.resolve()
    resolved_path = storage_path.resolve(strict=False)

    try:
        resolved_path.relative_to(upload_root)
    except ValueError as error:
        raise ValueError("Stored file path is outside the upload directory") from error

    if not resolved_path.exists():
        return None
    if not resolved_path.is_file():
        raise ValueError("Stored upload path is not a file")

    staged_path = upload_root / f".{uuid4().hex}.deleting"
    resolved_path.replace(staged_path)
    return StagedFileDeletion(
        original_path=resolved_path,
        staged_path=staged_path,
    )
