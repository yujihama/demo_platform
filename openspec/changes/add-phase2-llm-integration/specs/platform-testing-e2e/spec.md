## ADDED Requirements

### Requirement: LLM Pipeline E2E Test
The E2E test suite SHALL include a test that exercises the full LLM pipeline for at least 2 application types (TYPE_DOCUMENT_PROCESSOR and TYPE_VALIDATION) with actual LLM calls (or mocked LLM responses).

#### Scenario: LLM pipeline test for document processor app
- **WHEN** E2E test submits natural language requirements for a document processing app
- **THEN** the backend SHALL invoke Agents 1-4 and validator successfully
- **AND** the generated app SHALL match the document processor template structure
- **AND** the test SHALL verify the ZIP package contains expected files

#### Scenario: LLM pipeline test for validation app
- **WHEN** E2E test submits natural language requirements for a validation app
- **THEN** the backend SHALL invoke Agents 1-4 and validator successfully
- **AND** the generated app SHALL match the validation template structure
- **AND** the test SHALL verify the ZIP package contains expected files

### Requirement: LLM Error Handling Test
The E2E test suite SHALL include a test that verifies LLM error handling (rate limits, API failures) and retry logic.

#### Scenario: LLM retry logic tested
- **WHEN** the test simulates transient LLM errors (429 rate limit)
- **THEN** the backend SHALL retry with exponential backoff
- **AND** after successful retry, the generation SHALL complete
- **AND** if all retries fail, the job status SHALL be FAILED with error message

## MODIFIED Requirements

### Requirement: UI Invoice Flow Test
The test suite SHALL include an end-to-end UI test that drives the seven-step wizard for the invoice validation scenario and verifies the ZIP download link. テストケースは UI 操作でフローを完走しなければならない。The UI wizard test SHALL support both mock and LLM modes, with LLM mode using mocked LLM responses.

#### Scenario: UI wizard test passes
- **WHEN** テストが要件入力からパッケージダウンロードまでを自動操作したとき
- **THEN** それぞれのステップで想定されたモックのレスポンスが表示されなければならない
- **AND** 最終ステップでダウンロードボタンが有効化され、HTTP 200 のレスポンスを受け取らなければならない

#### Scenario: UI wizard with LLM mode
- **WHEN** E2E test configures LLM mode with mocked responses
- **THEN** the UI SHALL submit natural language requirements
- **AND** the backend SHALL process with LLM agents
- **AND** the UI SHALL display progress for all agent steps
- **AND** the download button SHALL be enabled on completion

### Requirement: CLI Generation Test
The test suite SHALL execute the CLI `generate` command and verify that `output/` contains the ZIP and `metadata.json` with exit code 0. 生成物の内容を検証しなければならない。The CLI generation test SHALL support both mock and LLM modes, with LLM mode using mocked LLM responses.

#### Scenario: CLI e2e test validates artifacts
- **WHEN** テストが `python backend/cli.py generate --config tests/e2e/fixtures/invoice.yaml` を実行したとき
- **THEN** 終了コード 0 が返されなければならない
- **AND** 指定パスに Zip ファイルとメタデータが存在し、その内容が期待されるファイル群を含んでいなければならない

#### Scenario: CLI generation with LLM mode
- **WHEN** E2E test runs CLI with LLM mode configuration and mocked responses
- **THEN** the CLI SHALL process requirements through LLM agents
- **AND** the output SHALL include progress for all agent steps
- **AND** the exit code SHALL be 0 on success

