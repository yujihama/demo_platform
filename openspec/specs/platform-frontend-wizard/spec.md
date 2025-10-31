# platform-frontend-wizard Specification

## Purpose
TBD - created by archiving change add-phase1-mvp-foundation. Update Purpose after archive.
## Requirements
### Requirement: Seven Step Wizard Navigation
The frontend SHALL present the Phase 1 seven-step generation flow (hearing through packaging) as a wizard so that users can advance sequentially. 各ステップは履歴に基づき戻る操作も許容しなければならない。

#### Scenario: User advances through seven steps
- **WHEN** ユーザーがステップ完了ボタンを押下したとき
- **THEN** ウィザードは次のステップへ遷移しなければならない
- **AND** 進行状況ヘッダーには 7 つのステップ名と現在位置が表示されていなければならない

### Requirement: Requirement Intake Screen
The frontend SHALL provide a free-form requirement intake form (textarea plus submit button) during step 1. 入力内容はバックエンド API に送信される前に空判定などの基本バリデーションを行わなければならない。

#### Scenario: Requirement prompt submission
- **WHEN** ユーザーが要件テキストを入力して送信ボタンを押下したとき
- **THEN** フロントエンドはモック用のバックエンド API を呼び出し、成功レスポンスを受け取るまでローディング状態を表示しなければならない
- **AND** 空文字の場合は送信をブロックし、バリデーションエラーメッセージを表示しなければならない

### Requirement: Mock Preview Approval Screen
The frontend SHALL display a fixed UI mock (image or HTML) at step 3 and allow the user to approve or send back the design. 承認を得た場合のみ以降の生成処理へ進めなければならない。

#### Scenario: User approves mock preview
- **WHEN** ユーザーが承認ボタンを押下したとき
- **THEN** フロントエンドは承認イベントをバックエンドに送信し、次ステップへ遷移しなければならない
- **AND** 差戻しを選択した場合は要件入力ステップへ戻らなければならない

### Requirement: Progress Feedback and Logs
The frontend SHALL render progress updates and summary logs for steps 4 through 6 (template render, test data generation, E2E test) via polling or SSE. 各ステップの完了時にはチェックマークを付与しなければならない。

#### Scenario: Progress updates rendered to user
- **WHEN** バックエンドから各ステップの進行状態が更新されたとき
- **THEN** フロントエンドは該当ステップのステータスラベルを更新しなければならない
- **AND** ローディング表示が完了ステータスに変わる際、完了メッセージを記録として残さなければならない

### Requirement: Download Delivery Screen
The frontend SHALL show a download button for the generated ZIP package and a rerun link during step 7. ダウンロードリンクはバックエンドのジョブ API から取得した URL を利用しなければならない。

#### Scenario: User downloads generated package
- **WHEN** バックエンドがダウンロード URL を返却したとき
- **THEN** フロントエンドはダウンロードボタンを有効化しなければならない
- **AND** ユーザーがボタンを押下すると Zip ファイルのダウンロードが開始されなければならない

