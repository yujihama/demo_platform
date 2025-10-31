# platform-cli-generation Specification

## Purpose
TBD - created by archiving change add-phase1-mvp-foundation. Update Purpose after archive.
## Requirements
### Requirement: Generate Command Entry Point
The CLI SHALL expose a `generate` command executable as `python backend/cli.py generate --config <path>` during Phase 1. コマンドはバックエンドと同一の生成フローを同期的に実行しなければならない。

#### Scenario: CLI generates invoice validation app
- **WHEN** ユーザーが `python backend/cli.py generate --config config/examples/invoice.yaml` を実行したとき
- **THEN** CLI は設定ファイルを読み込み、バックエンドサービスもしくは直接内部ロジックを介して生成フローを起動しなければならない
- **AND** 実行完了後に生成成果物のパスとダウンロードに相当するファイル位置を標準出力へ表示しなければならない

### Requirement: Config Driven Inputs
The CLI SHALL read user ID, project ID, requirement text, and template selection from a YAML configuration file and provide Phase 1 defaults for the invoice validation app. 設定値は読み込み時に検証されなければならない。

#### Scenario: CLI loads config overrides
- **WHEN** 設定ファイルに要件テキストや出力ルートが定義されているとき
- **THEN** CLI は設定値を検証し、欠落している必須項目があればエラーを表示しなければならない
- **AND** 既定値が使用される場合は、その旨をログに記録しなければならない

### Requirement: Console Progress Feedback
The CLI SHALL print progress for each generation step (requirements, templates, test data, E2E tests, packaging) to stdout and emit a completion summary. 完了時にはサマリーログを出力しなければならない。

#### Scenario: CLI prints step updates
- **WHEN** 各処理ステップが開始・完了したとき
- **THEN** CLI はステップ名と状態を含む行を標準出力に表示しなければならない
- **AND** 処理が完了した場合は成功メッセージを表示し、失敗した場合はエラー詳細を表示しなければならない

### Requirement: Output Directory Consistency
The CLI SHALL persist results using the same hierarchy as the backend (`output/{user_id}/{project_id}/app.zip` and `metadata.json`). ディレクトリが存在しない場合は自動作成しなければならない。

#### Scenario: CLI stores artifacts under output hierarchy
- **WHEN** CLI 実行時に `output/` 配下に該当ユーザーとプロジェクトのディレクトリが存在しないとき
- **THEN** CLI はディレクトリを作成しなければならない
- **AND** 生成完了後に Zip とメタデータをその配下へ保存しなければならない

### Requirement: Failure Exit Codes
The CLI SHALL exit with a non-zero status code whenever the generation flow fails and MUST print the failing step and reason to stderr. 標準エラー出力にはトラブルシューティングに必要なメッセージを表示しなければならない。

#### Scenario: CLI surfaces failure state
- **WHEN** テンプレート出力やテスト実行が失敗したとき
- **THEN** CLI は終了コード 1 を返さなければならない
- **AND** 標準エラー出力に失敗ステップの識別子とトラブルシューティングに必要なメッセージを表示しなければならない

