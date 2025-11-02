# デモアプリケーション生成プラットフォーム

LLM統合による自然言語でのアプリケーション生成プラットフォームです。ユーザーはチャットUIで「請求書からデータを抽出するアプリを作って」と入力するだけで、システムが`workflow.yaml`を生成し、実行可能なDockerパッケージとしてダウンロードできます。

## 主な機能

- **自然言語によるアプリ生成**: チャットUIで要件を入力すると、LLMエージェントが`workflow.yaml`を自動生成
- **宣言的ワークフロー実行**: 生成された`workflow.yaml`を汎用実行エンジンが解釈し、動的にUIを構築
- **即座に実行可能なパッケージ**: Docker ComposeファイルとREADMEを含む完全なパッケージをダウンロード
- **CLI生成フロー**: コマンドラインからも同一の生成パイプラインを実行可能

## 必要要件

- Python 3.11 以上
- Node.js 18 以上 (npm または yarn)
- Docker / Docker Compose v2

## 環境構築

1. ルートディレクトリで `.env.example` をコピーして `.env` を作成します。

   ```powershell
   Copy-Item .env.example .env
   ```

2. バックエンド依存関係をインストールします。

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate
   pip install -r backend\requirements.txt
   ```

3. フロントエンド依存関係をインストールします。

   ```powershell
   cd frontend
   npm install
   cd ..
   ```

4. Docker Compose でホットリロード付きの開発環境を起動します。

   ```powershell
   docker compose up --build
   ```

バックエンドは `http://localhost:${BACKEND_PORT}` (デフォルト `8000`)、フロントエンドは `http://localhost:${FRONTEND_PORT}` (デフォルト `5173`) でアクセスできます。Redis は `localhost:${REDIS_PORT}`、Dify モックサーバーは `http://localhost:3000` に起動します。

## LLM対話によるアプリ生成（Phase 3）

フロントエンドのチャットUIから自然言語でアプリケーションを生成できます。

1. **チャットUIで要件を入力**: 「請求書からデータを抽出するアプリを作って」などの自然言語プロンプトを入力
2. **自動生成**: LLMエージェントが要件を分析し、`workflow.yaml`を生成
3. **プレビュー確認**: 生成された`workflow.yaml`をブラウザで確認
4. **パッケージダウンロード**: 実行に必要なすべてを含むZIPファイルをダウンロード
5. **即座に実行**: `docker-compose up`でアプリケーションを起動

### 生成フローの詳細

生成プロセスは以下のステップで実行されます：

1. **要件分析**: ユーザーのプロンプトから要件を抽出
2. **アーキテクチャ設計**: 適切なワークフロー構造を設計
3. **YAML生成**: `workflow.yaml`を生成（自己修正ループにより品質を保証）
4. **バリデーション**: スキーマ検証とLLM検証を実施
5. **パッケージング**: Docker Compose、README、.env.exampleを含むZIPを作成

## 宣言的ワークフロー実行

`workflow.yaml` に定義された UI / パイプラインを汎用実行エンジンが解釈します。

- フロントエンドは `/api/runtime/workflow` を読み取り、`ui.steps` に従ってウィザードを構築します。
- ファイルアップロードなどの入力はセッション (`/api/runtime/sessions`) 経由でバックエンドに送信されます。
- バックエンドは Redis にセッション状態を保存し、`call_workflow` コンポーネントで Dify / モック API を呼び出します。
- 実行結果は `view.*` として公開され、UI コンポーネント（テーブル等）が動的に描画されます。

`workflow.yaml` を編集して `docker compose up` し直すだけで挙動を変更できます。モックサーバーは `http://localhost:3000/v1/workflows/<workflow_id>/run` を提供し、入力値をエコーした動的レスポンスを返します。

## CLI 生成フロー

CLI からは `backend/cli.py` を利用して同一の生成パイプラインを実行できます。

```powershell
python -m backend.cli generate --config config\examples\invoice.yaml
```

生成結果は `output/<user_id>/<project_id>/` に Zip と `metadata.json` が出力されます。

## テンプレートとモックデータ

- テンプレート: `templates/`
- モック仕様書: `mock/specs/`
- 宣言的ワークフロー: `workflow.yaml`
- 生成成果物: `output/`

## API エンドポイント

### 対話API（Phase 3）

- `POST /api/generate/conversations`: 新しい対話セッションを開始し、ワークフロー生成を開始
- `GET /api/generate/conversations/{session_id}`: 対話ステータスとメッセージを取得
- `GET /api/generate/conversations/{session_id}/workflow`: 生成された`workflow.yaml`を取得
- `GET /api/generate/conversations/{session_id}/download`: パッケージをZIPファイルとしてダウンロード

### 実行エンジンAPI

- `GET /api/runtime/workflow`: 現在の`workflow.yaml`定義を取得
- `POST /api/runtime/sessions`: 新しいワークフロー実行セッションを作成
- `POST /api/runtime/sessions/{session_id}/execute`: ワークフローステップを実行

## テスト

Playwright + pytest による UI/CLI E2E テストは `tests/e2e` に配置します。セットアップ後に以下で実行できます。

```powershell
pytest tests\e2e
```

Phase 3の対話フローのE2Eテストも含まれています：

```powershell
pytest tests\e2e\test_conversation_flow.py
```

PowerShell スクリプト `scripts\run-e2e.ps1` で UI/CLI テストと生成アプリの疎通確認を一括実行できます。

```powershell
pwsh scripts\run-e2e.ps1
```

## アーキテクチャ概要

### Phase 3 統合アーキテクチャ

- **LLMエージェントパイプライン**: 自然言語を`workflow.yaml`に変換するマルチエージェントシステム
- **対話セッション管理**: Redisまたはファイルシステムベースのセッションストレージ
- **汎用実行エンジン**: `workflow.yaml`を解釈して動的にUIとパイプラインを実行
- **動的UI生成**: 実行時に`workflow.yaml`からReactコンポーネントを構築

### 生成パッケージの構成

ダウンロードされるZIPファイルには以下が含まれます：

- `workflow.yaml`: アプリケーションの定義
- `docker-compose.yml`: 実行環境の定義（runtime-engine, runtime-ui, redis）
- `.env.example`: 環境変数のテンプレート
- `README.md`: セットアップと実行手順

パッケージを展開して`docker-compose up`を実行するだけで、生成されたアプリケーションが起動します。

