## ADDED Requirements

### Requirement: LLM Provider Abstraction Layer
The backend SHALL provide an LLM abstraction layer using LangChain that supports multiple providers (OpenAI, Azure OpenAI) configured via `config/llm.yaml`. The LLMFactory MUST create LLM instances through LangChain's `ChatOpenAI` class and handle provider-specific configurations.

#### Scenario: LLM instance created for OpenAI provider
- **WHEN** `config/llm.yaml` has `provider: openai` with valid `providers.openai.api_key`
- **THEN** LLMFactory SHALL create a LangChain ChatOpenAI instance with the configured model and temperature
- **AND** the instance SHALL be ready to use with structured output

#### Scenario: LLM instance created for Azure OpenAI provider
- **WHEN** `config/llm.yaml` has `provider: azure_openai` with required Azure settings
- **THEN** LLMFactory SHALL create a LangChain ChatOpenAI instance configured for Azure endpoints and deployment
- **AND** the instance SHALL be ready to use with structured output

### Requirement: LLM Configuration Management
The backend SHALL extend `config/llm.yaml` to support provider-specific settings including API keys, model names, temperature, and Azure-specific configurations (endpoint, deployment, API version).

#### Scenario: LLM configuration loaded from YAML
- **WHEN** ConfigManager loads `config/llm.yaml`
- **THEN** the LLMConfig model SHALL parse provider settings for OpenAI and Azure OpenAI
- **AND** missing required settings SHALL raise validation errors at startup

### Requirement: Retry Logic with Exponential Backoff
The backend SHALL implement exponential backoff retry logic for LLM API calls with configurable max attempts and initial delay. Retries SHALL be triggered on transient errors (network issues, rate limits) but not on validation errors.

#### Scenario: LLM API retry on transient error
- **WHEN** an LLM API call fails with a transient error (429, 503, network timeout)
- **THEN** the system SHALL retry with exponentially increasing delay (1s, 2s, 4s) up to 3 times
- **AND** after max retries, the error SHALL be reported to the user

#### Scenario: LLM API no retry on validation error
- **WHEN** an LLM API call fails with a validation error (400, 401)
- **THEN** the system SHALL NOT retry and immediately report the error

### Requirement: Agent 1 - Requirements Decomposition
The backend SHALL implement a requirements decomposition agent that takes natural language input and outputs structured requirements using Pydantic models. The agent MUST use LangChain's structured output feature.

#### Scenario: Agent decomposes user requirements
- **WHEN** a user submits natural language requirements (e.g., "I want an app to validate invoices")
- **THEN** Agent 1 SHALL output a structured requirements list with IDs, descriptions, and types (input/processing/output)
- **AND** the output SHALL conform to the RequirementsSchema Pydantic model

### Requirement: Agent 2 - Application Type Classification
The backend SHALL implement an application type classification agent that analyzes requirements and classifies the application into one of the predefined types (TYPE_CRUD, TYPE_DOCUMENT_PROCESSOR, TYPE_VALIDATION, TYPE_ANALYTICS, TYPE_CHATBOT).

#### Scenario: Agent classifies app type
- **WHEN** Agent 2 receives structured requirements
- **THEN** it SHALL classify the application type with a confidence score
- **AND** it SHALL recommend a template structure matching the app type

### Requirement: Agent 3 - Component Selection
The backend SHALL implement a component selection agent that selects UI components from the catalog based on requirements, app type, and recommended template.

#### Scenario: Agent selects components
- **WHEN** Agent 3 receives requirements, app type, and template
- **THEN** it SHALL select specific UI components with positions, props, and requirement mappings
- **AND** each selected component SHALL fulfill at least one requirement

### Requirement: Agent 4 - Data Flow Design
The backend SHALL implement a data flow design agent that defines data flow between selected components, including triggers, API calls, and state variables with type safety.

#### Scenario: Agent designs data flow
- **WHEN** Agent 4 receives selected components and requirements
- **THEN** it SHALL output a structured data flow with steps, triggers, source/target components, API calls, and type definitions
- **AND** the data flow SHALL ensure all requirements are fulfilled

### Requirement: Validator Agent
The backend SHALL implement a validator agent that verifies the generated specification for:
1. Component existence in catalog
2. API existence in Dify catalog
3. Type consistency between component outputs and inputs
4. No circular dependencies
5. All requirements fulfilled

#### Scenario: Validator succeeds
- **WHEN** the validator receives a complete specification
- **THEN** it SHALL check all validation rules
- **AND** if all checks pass, it SHALL return success and proceed to template generation

#### Scenario: Validator fails and retries
- **WHEN** the validator detects errors (e.g., component not in catalog)
- **THEN** it SHALL return detailed error messages
- **AND** the system SHALL retry Agent 3 (Component Selection) up to 3 times
- **AND** if retries exhaust, the error SHALL be reported to the user

## MODIFIED Requirements

### Requirement: Mock Agent Pipeline
The backend SHALL produce application specifications through a deterministic mock agent layer during Phase 1 instead of invoking an LLM. モック結果はリポジトリ内の JSON 定義を返却し、各ステップの出力を永続化して進捗を可視化しなければならない。The backend SHALL produce application specifications through either a deterministic mock agent layer (Phase 1) or a multi-agent LLM pipeline (Phase 2) based on configuration. The pipeline SHALL support switching between modes via `config/features.yaml`.

#### Scenario: Mock pipeline returns deterministic spec
- **WHEN** 生成ジョブが受理され Phase 1 設定 (`agents.use_mock = true`) が有効なとき
- **THEN** モックエージェントは固定化された請求書検証アプリ仕様を返却しなければならない
- **AND** バックエンドは仕様書を保存して後続のテンプレート埋め込み処理へ渡さなければならない

#### Scenario: LLM pipeline generates dynamic spec
- **WHEN** `agents.use_mock` is `false` in `config/features.yaml`
- **THEN** the pipeline SHALL invoke Agents 1-4 sequentially with the user's natural language input
- **AND** after Agent 4, the validator SHALL verify the specification
- **AND** on validation failure, Agent 3 SHALL retry up to 3 times before reporting to user


