# デモアプリケーション生成プラットフォーム

自然言語の要件から `workflow.yaml` を生成し、汎用実行エンジンと動的 UI が実行可能な Docker パッケージを出力するプラットフォームです。Phase 3 では LLM エージェントと宣言的実行エンジンを統合し、チャット UI からワンストップでアプリを体験できるようになりました。

## 主な機能

- **LLM 対話生成**: 「請求書からデータを抽出するアプリを作って」といった自然言語プロンプトをチャット UI で入力すると、エージェントが要件を分析して `workflow.yaml` を作成します。
- **即時プレビュー**: 生成された `workflow.yaml` をブラウザ上で確認し、成果物に含まれる内容を把握できます。
- **ワンクリック配布パッケージ**: `workflow.yaml`・配布用 `docker-compose.yml`・`.env.example`・README を含んだ zip をダウンロードできます。
- **汎用実行エンジン**: ダウンロードしたパッケージを展開し `docker-compose up` するだけで、生成したアプリをブラウザで動作させられます。

## 必要要件

- Python 3.11 以上
- Node.js 18 以上 (npm または yarn)
- Docker / Docker Compose v2

## 開発環境セットアップ

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

## 生成フローの使い方

1. ブラウザでフロントエンド (`http://localhost:5173`) にアクセスします。
2. 「プロジェクト設定」にユーザー ID / プロジェクト ID / プロジェクト名を入力します。
3. 要件プロンプトに自然言語で指示を入力し、「会話を開始」をクリックします。
4. 画面中央のチャットに LLM の思考過程が表示され、workflow.yaml が完成するとプレビュー欄に内容が表示されます。
5. 「パッケージをダウンロード」を押すと zip ファイルが取得できます。

ダウンロードした zip を展開し、同梱の README に従って `.env` を編集後、以下を実行すると生成アプリが立ち上がります。

```bash
docker-compose up -d
```

## 汎用実行エンジンについて

- フロントエンドは `/api/runtime/workflow` を読み取り、`ui.steps` に従ってウィザードを自動生成します。
- 入力値は `/api/runtime/sessions` API を通じてステートフルに管理され、Redis に保存されます。
- `pipeline.steps` では `call_workflow` や `file_uploader` などの汎用コンポーネントを組み合わせ、Dify / モック API と連携します。
- `workflow.yaml` を更新して再起動するだけでアプリの挙動を変更できます。

## CLI からの利用

CLI でも同一の LLM パイプラインを実行できます。

```powershell
python -m backend.cli generate --config config\examples\invoice.yaml
```

生成結果は `output/<user_id>/<project_id>/` に zip (`app.zip`) と `metadata.json` が出力されます。

## リポジトリ構成

- `backend/` … FastAPI ベースの生成 API・runtime API
- `frontend/` … LLM 対話 UI (Vite + React + MUI)
- `mock/` … モック仕様書および Dify モックサーバー
- `output/` … 生成済みパッケージの格納先
- `workflow.yaml` … 汎用実行エンジンが読み込む宣言的設定

## テスト

Playwright + pytest による UI/CLI E2E テストは `tests/e2e` に配置します。セットアップ後に以下で実行できます。

```powershell
pytest tests\e2e
```

PowerShell スクリプト `scripts\run-e2e.ps1` で UI/CLI テストと生成アプリの疎通確認を一括実行できます。

```powershell
pwsh scripts\run-e2e.ps1
```
