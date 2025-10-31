## Context
- Phase 1 (MVP) では LLM や Dify の実装をモックに置き換えつつ、UI/CLI からエンドツーエンドなアプリ生成体験を成立させる必要がある。
- アーキテクチャレビューおよび技術設計書に基づき、FastAPI バックエンドを中心とした生成パイプライン、React ウィザード UI、CLI、Playwright テストを同時に立ち上げる。
- 生成されるアプリはテンプレートベースで React/FastAPI/Docker を組み合わせ、Zip 配布する。

## Goals / Non-Goals
- Goals:
  - モックエージェントとテンプレート生成を利用し、UI/CLI 双方から請求書検証アプリを生成できるようにする
  - 生成結果を Zip/metadata として `output/` に保存し、ダウンロードリンクを提供する
  - Playwright による UI/CLI E2E テストで Phase 1 完了条件を自動検証できるようにする
- Non-Goals:
  - 実際の LLM 呼び出しや Dify 連携の実装（Phase 2 以降）
  - Embedding 検索やテンプレートバージョニングなどスケール機構の実装

## Decisions
- Backend: FastAPI に `/api/generate` などの REST エンドポイントを実装し、設定でモックのオン/オフを制御する。モック仕様は JSON ファイルとして管理し、テンプレートエンジン (Jinja2) に渡す。
- Generation Outputs: `templates/` に React/FastAPI/Docker/Playwright 用テンプレートを配置し、ジョブごとに一時ディレクトリへ展開して Zip 圧縮する。`metadata.json` に仕様書・設定・バージョン情報を記録する。
- Frontend: React 18 + MUI v5 を採用し、7 ステップウィザード、静的モックプレビュー、進捗表示、ダウンロード画面を実装する。バックエンドの進捗 API をポーリングで取得する。
- CLI: `backend/cli.py` に `generate` サブコマンドを実装し、YAML 設定 (`config/`) を読み込んでバックエンドと同じパイプラインを同期実行する。出力場所やユーザー識別子は設定ファイルで上書き可能にする。
- Testing: Playwright (Python) + pytest を採用し、UI ウィザードと CLI コマンド双方の Happy Path を自動化。テストデータは Faker ベースのユーティリティで生成する。

## Risks / Trade-offs
- Mock と本実装の差異: Phase 2 で LLM を導入する際に I/O 形式がズレるリスク → モック仕様と Pydantic モデルを整合させ、Structured Output を前提としたデータ構造で設計する。
- 生成ファイルの肥大化: テンプレートが多岐に渡ると保守が難しくなる → Phase 1 では請求書検証アプリ用の最小テンプレートセットに限定し、将来はテンプレートバージョニングを導入する。
- 進捗表示の遅延: ポーリング間隔が長いと UX が悪化、短いと負荷が高い → 初期は 1〜2 秒間隔のポーリングにし、Phase 2 で SSE/WebSocket への移行を検討する。

## Migration Plan
1. モック仕様・テンプレート・設定ファイルを整備してバックエンドの生成パイプラインを構築する。
2. React ウィザード UI を接続し、モックレスポンスで UI フローを検証する。
3. CLI コマンドを追加し、バックエンドロジックの再利用を実装する。
4. Playwright UI テストと CLI テストを作成し、Phase 1 の受入基準を自動化する。
5. CI スクリプトで UI/CLI テストとパッケージ確認を一括実行できるようにする。

## Open Questions
- モック仕様書のバージョン管理方法（単一 JSON で十分か、将来的に複数パターンをどう切り替えるか）
- ダウンロード URL の有効期限やアクセス制御を Phase 1 でどこまで厳密に扱うか
- CLI からの実行時にバックエンド API を呼ぶか、同一プロセスで処理するかの最終選択（再利用性と実行速度のトレードオフ）

