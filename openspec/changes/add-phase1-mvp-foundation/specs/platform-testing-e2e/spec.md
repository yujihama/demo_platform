## ADDED Requirements
### Requirement: Playwright Test Harness
The test suite SHALL adopt Playwright (Python) in Phase 1 and provide a shared harness under `tests/e2e/` that exercises UI and CLI flows. テストは `pytest` で実行可能な構成になっていなければならない。

#### Scenario: Playwright tests execute via pytest
- **WHEN** 開発者が `pytest tests/e2e` を実行したとき
- **THEN** Playwright のブラウザ起動と後片付けが自動で行われなければならない
- **AND** UI/CLI 双方のテストケースが検出され実行されなければならない

### Requirement: UI Invoice Flow Test
The test suite SHALL include an end-to-end UI test that drives the seven-step wizard for the invoice validation scenario and verifies the ZIP download link. テストケースは UI 操作でフローを完走しなければならない。

#### Scenario: UI wizard test passes
- **WHEN** テストが要件入力からパッケージダウンロードまでを自動操作したとき
- **THEN** それぞれのステップで想定されたモックのレスポンスが表示されなければならない
- **AND** 最終ステップでダウンロードボタンが有効化され、HTTP 200 のレスポンスを受け取らなければならない

### Requirement: CLI Generation Test
The test suite SHALL execute the CLI `generate` command and verify that `output/` contains the ZIP and `metadata.json` with exit code 0. 生成物の内容を検証しなければならない。

#### Scenario: CLI e2e test validates artifacts
- **WHEN** テストが `python backend/cli.py generate --config tests/e2e/fixtures/invoice.yaml` を実行したとき
- **THEN** 終了コード 0 が返されなければならない
- **AND** 指定パスに Zip ファイルとメタデータが存在し、その内容が期待されるファイル群を含んでいなければならない

### Requirement: Test Data Fixtures
The test suite SHALL provide Faker-based utilities that prepare reusable dummy data for both UI and CLI tests, storing them under `tests/e2e/test_data/`. 生成データはテスト前に準備されなければならない。

#### Scenario: Test data prepared before runs
- **WHEN** テスト実行前にフィクスチャが呼び出されたとき
- **THEN** 指定パスに必要な CSV や JSON のテストデータが生成されなければならない
- **AND** テスト終了後に後片付けするためのクリーンアップ処理が用意されていなければならない

### Requirement: Pipeline Integration
The test suite SHALL expose a single command (Makefile target or PowerShell script) that runs both UI and CLI E2E tests for Phase 1 acceptance and MUST return a non-zero exit code when any test fails. コマンドは CI から再利用できる形でドキュメント化されなければならない。

#### Scenario: Single command validation
- **WHEN** 開発者が用意された `pw-phase1-validate`（仮称）スクリプトを実行したとき
- **THEN** UI と CLI の E2E テストが連続して実行され、結果が統合レポートとして出力されなければならない
- **AND** いずれかのテストが失敗した場合は非ゼロ終了コードで終了しなければならない

