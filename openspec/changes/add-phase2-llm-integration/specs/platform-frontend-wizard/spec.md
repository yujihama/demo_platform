## MODIFIED Requirements

### Requirement: Requirement Intake Screen
The frontend SHALL provide a free-form requirement intake form (textarea plus submit button) during step 1 that supports multi-line natural language input for LLM mode. Input content SHALL be validated for non-empty strings before submission. 入力内容はバックエンド API に送信される前に空判定などの基本バリデーションを行わなければならない。

#### Scenario: Requirement prompt submission
- **WHEN** ユーザーが要件テキストを入力して送信ボタンを押下したとき
- **THEN** フロントエンドはモック用のバックエンド API を呼び出し、成功レスポンスを受け取るまでローディング状態を表示しなければならない
- **AND** 空文字の場合は送信をブロックし、バリデーションエラーメッセージを表示しなければならない

#### Scenario: Natural language requirement submission for LLM
- **WHEN** a user types multi-line natural language requirements in the textarea and clicks submit in LLM mode
- **THEN** the frontend SHALL send the requirements as plain text to POST /api/generate
- **AND** the backend SHALL use this text for LLM processing when `use_mock: false`
- **AND** empty input SHALL be blocked with a validation error message

### Requirement: Mock vs LLM Mode Toggle
The frontend SHALL provide a developer toggle (checkbox or switch) to switch between mock and LLM modes, visible only when enabled by configuration.

#### Scenario: Developer mode toggle
- **WHEN** developer mode is enabled in configuration
- **THEN** a toggle SHALL be visible on the requirements input screen
- **AND** changing the toggle SHALL add/remove a `use_mock` parameter in the API request

### Requirement: Progress Feedback and Logs
The frontend SHALL render progress updates for both mock and LLM pipeline steps via polling or SSE. For LLM mode, progress SHALL include individual agent steps.

#### Scenario: LLM pipeline progress displayed
- **WHEN** the backend is processing with LLM agents
- **THEN** the frontend SHALL display progress for: requirements_decomposition → app_type_classification → component_selection → data_flow_design → validation
- **AND** each completed agent step SHALL show a checkmark
- **AND** the current running step SHALL show a spinner

## ADDED Requirements

### Requirement: LLM Error Display
The frontend SHALL display LLM-specific errors (API failures, validation failures) with actionable error messages in the ErrorBanner component.

#### Scenario: LLM API error shown to user
- **WHEN** the backend returns an LLM API error (rate limit, API key invalid, network issue)
- **THEN** the ErrorBanner SHALL display the error message from the backend
- **AND** the error message SHALL suggest troubleshooting steps when applicable

#### Scenario: Validation error after retries shown to user
- **WHEN** the validator fails after 3 retries
- **THEN** the ErrorBanner SHALL display the validation errors in a user-friendly format
- **AND** the wizard SHALL allow the user to modify requirements and resubmit

