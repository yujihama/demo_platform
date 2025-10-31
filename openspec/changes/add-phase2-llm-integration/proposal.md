## Why
Phase 1で構築したモックベースの基盤の上に、実際のLLMを統合し、ユーザーの自然言語要件から動的にアプリケーションを生成する機能を実現する。これにより、プラットフォームは単なるテンプレートエンジンから、AI駆動の真の自動生成システムへと進化する。

## What Changes
- LLM抽象化レイヤーを実装し、OpenAIとAzure OpenAIの両方をサポート可能にする
- 4つの専門エージェント（要件分解、アプリタイプ分類、パーツ選択、データフロー設計）とバリデーターエージェントを実装
- パイプラインを拡張し、モック処理とLLM処理を切り替え可能にする
- リトライロジック（Exponential Backoff）とエラーハンドリングを実装
- UI/CLIの両方で自然言語要件入力に対応
- 少なくとも2つのアプリタイプ（TYPE_DOCUMENT_PROCESSOR、TYPE_VALIDATION）で動作することを検証

## Impact
- Affected specs: `platform-backend-app-generation`, `platform-frontend-wizard`, `platform-testing-e2e`
- Affected code: `backend/app/services/`, `backend/app/config.py`, `config/llm.yaml`, `frontend/src/`, `tests/e2e/`
- New dependencies: `langchain-openai`, `openai` (Python), `pydantic` (already in use)

