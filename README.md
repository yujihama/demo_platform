# デモアプリケーション生成プラットフォーム

Phase 1 (MVP) のためのフロントエンド・バックエンド・CLI・E2E テストを備えた生成プラットフォームです。LLM/Dify はモック実装で置き換え、UI/CLI の双方からテンプレートベースのアプリ生成フローを体験できます。

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

バックエンドは `http://localhost:${BACKEND_PORT}` (デフォルト `8000`)、フロントエンドは `http://localhost:${FRONTEND_PORT}` (デフォルト `5173`) でアクセスできます。

## CLI 生成フロー

CLI からは `backend/cli.py` を利用して同一の生成パイプラインを実行できます。

```powershell
python -m backend.cli generate --config config\examples\invoice.yaml
```

生成結果は `output/<user_id>/<project_id>/` に Zip と `metadata.json` が出力されます。

## テンプレートとモックデータ

- テンプレート: `templates/`
- モック仕様書: `mock/specs/`
- 生成成果物: `output/`

## テスト

Playwright + pytest による UI/CLI E2E テストは `tests/e2e` に配置します。セットアップ後に以下で実行できます。

```powershell
pytest tests\e2e
```

PowerShell スクリプト `scripts\run-e2e.ps1` で UI/CLI テストと生成アプリの疎通確認を一括実行できます。

```powershell
pwsh scripts\run-e2e.ps1
```


