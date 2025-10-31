# platform-backend-app-generation Specification

## Purpose
TBD - created by archiving change add-phase1-mvp-foundation. Update Purpose after archive.
## Requirements
### Requirement: MVP Generation API
The backend SHALL expose REST endpoints that allow both UI and CLI clients to trigger the same Phase 1 generation flow. バックエンドは少なくとも `POST /api/generate` で生成ジョブを受付し、`GET /api/generate/{job_id}` で進捗とダウンロード URL を返却する OpenAPI 定義を提供しなければならない。

#### Scenario: UI initiates generation via REST
- **WHEN** UI クライアントが `POST /api/generate` に Phase 1 の請求書検証アプリ要件（モックID含む）を送信したとき
- **THEN** バックエンドはジョブ ID と初期ステータス `received` を応答しなければならない
- **AND** `GET /api/generate/{job_id}` を呼び出した際に、進捗ステップとパッケージダウンロード URL（完了時のみ）を返却しなければならない

### Requirement: Mock Agent Pipeline
The backend SHALL produce application specifications through a deterministic mock agent layer during Phase 1 instead of invoking an LLM. モック結果はリポジトリ内の JSON 定義を返却し、各ステップの出力を永続化して進捗を可視化しなければならない。

#### Scenario: Mock pipeline returns deterministic spec
- **WHEN** 生成ジョブが受理され Phase 1 設定 (`agents.use_mock = true`) が有効なとき
- **THEN** モックエージェントは固定化された請求書検証アプリ仕様を返却しなければならない
- **AND** バックエンドは仕様書を保存して後続のテンプレート埋め込み処理へ渡さなければならない

### Requirement: Template Based Code Generation
The backend SHALL use Jinja2 templates to render the React frontend, FastAPI backend, Playwright tests, Docker/Compose files, logging configuration, and test data from the mock specification. 各テンプレートを用いて生成物ディレクトリを構築しなければならない。

#### Scenario: Templates render into project structure
- **WHEN** モック仕様書がテンプレートエンジンに渡されたとき
- **THEN** システムは `generated/{job_id}/frontend`, `generated/{job_id}/backend`, `generated/{job_id}/tests`, `generated/{job_id}/docker` などのディレクトリを生成しなければならない
- **AND** それぞれのテンプレートにはアプリ名、UI パーツ、API エンドポイント、テストシナリオが埋め込まれていなければならない

### Requirement: Packaging Engine Output
The backend SHALL compress the generated artifacts into a ZIP file after successful template rendering and E2E tests, storing them under `output/{user_id}/{project_id}/app.zip` alongside `metadata.json`. Zip にはフロントエンド、バックエンド、Docker 設定、テストデータ、ログ設定が含まれていなければならない。

#### Scenario: Packaged artifact stored for download
- **WHEN** 生成ジョブの全ステップが成功したとき
- **THEN** バックエンドは Zip ファイルを `output/{user_id}/{project_id}/app.zip` に保存しなければならない
- **AND** 同階層に仕様書・実行設定を記録した `metadata.json` を保存しなければならない
- **AND** `GET /api/generate/{job_id}` のレスポンスにはダウンロード URL が含まれていなければならない

### Requirement: Configuration Driven Phase Control
The backend SHALL load phase configuration from YAML files so that `features.yaml` can toggle mock usage and execution mode. Phase 1 ではモックエージェントとモック Dify がデフォルトで有効化されていなければならない。

#### Scenario: Phase 1 settings enable mocks
- **WHEN** サービス起動時に `config/features.yaml` の `phase` が `mvp` に設定されているとき
- **THEN** バックエンドはモックエージェントとモック Dify 実装を有効化しなければならない
- **AND** 設定値は CLI からの実行時にも共通で参照されなければならない

