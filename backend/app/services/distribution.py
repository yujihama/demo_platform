"""Packaging service for delivering workflow runtime bundles."""

from __future__ import annotations

import textwrap
import zipfile
from pathlib import Path

from ..models.conversation import ConversationStatus
from .conversation import ConversationSession


class DistributionService:
    """Create distributable archives for generated workflows."""

    def __init__(self, *, output_root: Path | None = None) -> None:
        self._output_root = output_root or Path("generated/packages")
        self._output_root.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    def build_archive(self, session: ConversationSession) -> Path:
        if session.status != ConversationStatus.COMPLETED or not session.workflow_path:
            raise ValueError("workflow.yaml がまだ生成されていません。")

        target_dir = self._output_root / session.session_id
        target_dir.mkdir(parents=True, exist_ok=True)
        archive_path = target_dir / "app-package.zip"

        workflow_path = session.workflow_path
        docker_compose = self._render_docker_compose()
        readme = self._render_readme()

        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            bundle.write(workflow_path, arcname="workflow.yaml")
            bundle.writestr("docker-compose.yml", docker_compose)
            bundle.writestr("README.md", readme)

        return archive_path

    # ------------------------------------------------------------------
    @staticmethod
    def _render_docker_compose() -> str:
        return textwrap.dedent(
            """
            version: "3.9"

            services:
              runtime-engine:
                image: ghcr.io/demo-platform/runtime-engine:latest
                environment:
                  REDIS_URL: redis://redis:6379/0
                  WORKFLOW_FILE: /app/workflow.yaml
                volumes:
                  - ./workflow.yaml:/app/workflow.yaml:ro
                depends_on:
                  - redis

              runtime-ui:
                image: ghcr.io/demo-platform/runtime-ui:latest
                environment:
                  BACKEND_HOST: http://runtime-engine:8000
                ports:
                  - "8080:8080"
                depends_on:
                  - runtime-engine

              redis:
                image: redis:7-alpine
                volumes:
                  - redis_data:/data

            volumes:
              redis_data: {}
            """
        ).strip()

    # ------------------------------------------------------------------
    @staticmethod
    def _render_readme() -> str:
        return textwrap.dedent(
            """
            # 生成されたワークフローの実行方法

            このパッケージには `workflow.yaml`、最小構成の `docker-compose.yml`、実行手順を記載した README が含まれています。

            ## 事前準備

            1. Docker と Docker Compose v2 が利用できる環境を用意してください。
            2. `.env` ファイルを作成する必要はありません。必要な設定は `docker-compose.yml` に含まれています。

            ## 起動手順

            ```bash
            docker-compose up
            ```

            コマンド実行後、`runtime-ui` コンテナが公開するポート (デフォルト: 8080) にアクセスすることで、生成したアプリケーションを体験できます。

            ## コンテナの停止

            ```bash
            docker-compose down
            ```

            ## 注意事項

            - この構成は検証用です。本番運用ではセキュリティ設定や監視などを適宜追加してください。
            - `runtime-engine` や `runtime-ui` のイメージは社内レジストリから取得されることを想定しています。
            """
        ).strip()


distribution_service = DistributionService()

