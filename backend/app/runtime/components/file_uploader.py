"""Implementation of the `file_uploader` pipeline component."""

from __future__ import annotations

from typing import Any, Dict, Optional

from starlette.datastructures import UploadFile

from .base import ComponentHandler, ExecutionContext, ExecutionResult
from ..utils import build_path_value


class FileUploaderComponent(ComponentHandler):
    """Store uploaded files into the runtime session context."""

    requires_user_input = True

    async def execute(
        self,
        context: ExecutionContext,
        payload: Dict[str, Any],
        file: Optional[UploadFile] = None,
    ) -> ExecutionResult:
        if file is None:
            raise ValueError("ファイルが添付されていません。")

        params = context.step.params
        target_key = params.get("target_key")
        if not target_key:
            raise ValueError("file_uploader コンポーネントには target_key の指定が必要です。")

        encoding = params.get("encoding", "utf-8")
        as_text = params.get("as_text", True)

        content_bytes = await file.read()
        if as_text:
            try:
                stored_value: Any = content_bytes.decode(encoding)
            except UnicodeDecodeError as exc:  # pragma: no cover - guard clause
                raise ValueError("ファイルを指定したエンコーディングでデコードできませんでした。") from exc
        else:
            stored_value = content_bytes

        metadata = {
            "filename": file.filename,
            "size": len(content_bytes),
            "encoding": encoding if as_text else "binary",
        }

        metadata_key = params.get("metadata_key")

        private_updates = build_path_value(target_key, stored_value)
        public_updates = {}
        if metadata_key:
            public_updates = build_path_value(metadata_key, metadata)

        return ExecutionResult(
            public=public_updates,
            private=private_updates,
            step_output={"metadata": metadata},
        )


file_uploader = FileUploaderComponent()
