## Why
Phase 1 (MVP) では、LLM や Dify との連携前に、モックを用いたエンドツーエンドな生成フローを成立させ、UI/CLI の双方からアプリ生成を体験できる基盤を整える必要がある。

## What Changes
- フロントエンドに 7 ステップの生成ウィザードと固定モック表示を実装して、UI からモック経由の生成フローを完了できるようにする
- バックエンドにモックエージェント・テンプレートベースのコード生成・パッケージ化エンジンを実装し、固定仕様書から Docker 化済みアプリを Zip 配布する
- CLI から同一フローを呼び出す `generate` コマンドと設定ファイル読込を実装し、`output/` 配下へ成果物とメタデータを出力する
- Playwright を用いた UI/CLI 双方の E2E テストスケルトンを整備し、Phase 1 の完了条件を自動検証できるようにする

## Impact
- Affected specs: `platform-backend-app-generation`, `platform-frontend-wizard`, `platform-cli-generation`, `platform-testing-e2e`
- Affected code: `backend/app`, `backend/cli.py`, `frontend/`, `templates/`, `tests/e2e/`, `output/`

