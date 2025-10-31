## Context

Phase 1ではモックベースの生成フローを確立し、UI/CLI双方からアプリ生成を体験できる基盤を整えた。Phase 2では、実際のLLMを統合して、ユーザーの自然言語要件から動的にアプリケーションを生成する機能を実現する。

## Goals

- 複数のLLMプロバイダー（OpenAI、Azure OpenAI）をサポートする抽象化レイヤーの提供
- 階層的マルチエージェント方式による高品質な仕様書生成
- LLMエラー時の堅牢なリトライロジックの実装
- モックモードとLLMモードのシームレスな切り替え

## Non-Goals

- Phase 3のDify統合機能は対象外
- より高度なエージェント連携（並列実行など）は将来の拡張として保留

## Decisions

### Decision: LangChainを採用する
**What:** `langchain-openai` パッケージを使用してLLM抽象化レイヤーを実装する  
**Why:** OpenAIとAzure OpenAIを統一的に扱えるAPIを提供し、将来の他のプロバイダー追加も容易  
**Alternatives considered:**
- 純粋なOpenAI SDK: プロバイダー切り替え時にコード変更が必要
- 完全な独自実装: 開発工数が大きい

### Decision: PydanticモデルとLangChainのwith_structured_outputを使用する
**What:** すべてのエージェント出力をPydanticモデルで定義し、LangChainのwith_structured_outputで型安全な出力を保証する  
**Why:** 実行時エラーを削減し、コード補完とバリデーションを利用できる  
**Alternatives considered:**
- 手動でのJSON解析: 型安全性が保証されず、バリデーションも手動
- 外部スキーマツール: 追加ツールが必要で複雑

### Decision: Exponential Backoffでリトライロジックを実装する
**What:** LLM API呼び出し失敗時、初期遅延1秒、最大3回、指数バックオフ（1s, 2s, 4s）でリトライ  
**Why:** ネットワーク遅延やレート制限などの一時的エラーに対応  
**Alternatives considered:**
- Fixed delay: レート制限時にあまり効果的でない
- より長いバックオフ: ユーザー待ち時間が長くなる

### Decision: バリデーターエラー時のAgent 3再試行を3回まで許可する
**What:** バリデーション失敗時、Agent 3（パーツ選択）にエラー詳細をフィードバックして最大3回再試行  
**Why:** LLMの非決定性を考慮し、修正の機会を提供  
**Alternatives considered:**
- リトライなし: より頻繁にユーザー介入が必要になる
- より多くのリトライ: コストと時間の無駄が増える

## Risks / Trade-offs

### Risk: LLMの出力が不安定
**Mitigation:** 
- 温度パラメータを0.0に設定
- リトライロジックの実装
- バリデーターによる検証と再生成

### Risk: プロンプトエンジニアリングの難航
**Mitigation:**
- Few-shot Learningの活用
- 段階的なプロンプト改善
- チームでのプロンプトレビュー

### Risk: LLM APIのコスト超過
**Mitigation:**
- キャッシングの実装（将来の拡張）
- 軽量モデルの活用
- API利用状況のモニタリング

### Trade-off: 完全性 vs 開発速度
Phase 2では基本のアプリタイプ（TYPE_DOCUMENT_PROCESSOR、TYPE_VALIDATION）のみをサポート。他のタイプ（TYPE_CRUD、TYPE_ANALYTICS、TYPE_CHATBOT）は将来の拡張として保留。

## Migration Plan

### Phase 1 → Phase 2 移行
1. 設定ファイル（`config/llm.yaml`、`config/features.yaml`）を更新
2. モックモードは引き続きPhase 1の動作を維持
3. LLMモードを有効化すると新しいエージェントパイプラインが実行される
4. 下位互換性を維持: Phase 1のモック仕様はそのまま使用可能

### Rollback Plan
- `agents.use_mock: true` に設定することで即座にPhase 1モードに戻す
- LLM実装は既存のモック実装を壊さない設計

## Open Questions

- エージェント間のコンテキスト共有方法（逐次実行 vs 並列実行）: 現時点では逐次実行を採用し、将来的に並列実行を検討
- LLMレスポンスのキャッシング戦略: Phase 2では実装しないが、将来的にキャッシングレイヤーを追加

