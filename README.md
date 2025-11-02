# デモアプリケーション生成プラットフォーム

LLM とのチャットから `workflow.yaml` と配布用 Docker パッケージを生成し、汎用実行エンジンで宣言的にアプリケーションを動かすプラットフォームです。Phase 1/2 で構築したテンプレート生成基盤に加え、Phase 3 では LLM エージェントパイプラインと宣言的実行エンジンを統合し、自然言語による要件定義から配布・実行までを一気通貫で体験できます。

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

## LLM チャット生成フロー

1. フロントエンドトップの「アプリ生成チャット」に、自然言語で要件を入力して送信します。
2. バックエンドは `/api/generate/conversations` 経由で LLM エージェントパイプラインを実行し、`workflow.yaml` を自己修正ループ付きで生成します。
3. 生成完了後、画面に `workflow.yaml` のプレビューと配布用 Zip のダウンロードボタンが表示されます。
4. ダウンロードした Zip には `workflow.yaml`、`docker-compose.yml`、`.env.example`、`README.md` が含まれ、`docker-compose up` だけで実行環境を再現できます。

API から直接操作する場合は以下を利用します。

- セッション開始: `POST /api/generate/conversations`
- 進行状況取得: `GET /api/generate/conversations/{session_id}`
- 生成物取得: `GET /api/generate/conversations/{session_id}/workflow`
- パッケージダウンロード: `GET /api/generate/conversations/{session_id}/package/download`

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

チャット経由の生成結果は `output/<session_id>/` に `app.zip`、`workflow.yaml`、`metadata.json` が保存されます。CLI 生成では従来通り `output/<user_id>/<project_id>/` にテンプレートベースの成果物が配置されます。

## テンプレートとモックデータ

- テンプレート: `templates/`
- モック仕様書: `mock/specs/`
- 宣言的ワークフロー: `workflow.yaml`
- 生成成果物: `output/`（チャット生成は `output/<session_id>/`）

## テスト

Playwright + pytest による UI/CLI E2E テストは `tests/e2e` に配置します。セットアップ後に以下で実行できます。

```powershell
pytest tests\e2e
```

PowerShell スクリプト `scripts\run-e2e.ps1` で UI/CLI テストと生成アプリの疎通確認を一括実行できます。

```powershell
pwsh scripts\run-e2e.ps1
```


