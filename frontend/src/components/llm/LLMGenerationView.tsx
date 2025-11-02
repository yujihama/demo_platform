import {
  Alert,
  Box,
  Chip,
  Grid,
  List,
  ListItem,
  ListItemText,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import type { GenerationStatus } from "../../types";
import { StepDownload } from "../StepDownload";
import { StepProgress } from "../StepProgress";
import { CodeSnippet } from "../CodeSnippet";
import {
  parseWorkflowMetadata,
  RequirementMetadata,
  WorkflowAnalysisMetadata,
  WorkflowArchitectureMetadata,
  WorkflowValidationMetadata,
} from "../../utils/workflowMetadata";
import { useMemo } from "react";

type Props = {
  status: GenerationStatus | null;
  loading: boolean;
  onRestart: () => void;
};

export function LLMGenerationView({ status, loading, onRestart }: Props) {
  const metadata = useMemo(() => parseWorkflowMetadata(status?.metadata ?? null), [status?.metadata]);

  return (
    <Stack spacing={3} data-testid="llm-dashboard">
      <Grid container spacing={3}>
        <Grid item xs={12} md={4} display="grid" gap={3}>
          <StepProgress status={status} loading={loading} />
          <ValidationCard validation={metadata?.validation} />
          <StepDownload status={status} onRestart={onRestart} showMetadata={false} />
        </Grid>
        <Grid item xs={12} md={8} display="grid" gap={3}>
          <YamlPreview workflowYaml={metadata?.workflowYaml} />
          <AnalysisCard analysis={metadata?.analysis} />
          <ArchitectureCard architecture={metadata?.architecture} />
        </Grid>
      </Grid>
    </Stack>
  );
}

function YamlPreview({ workflowYaml }: { workflowYaml?: string }) {
  return (
    <Paper variant="outlined" sx={{ p: 3, display: "grid", gap: 2 }} data-testid="llm-yaml-preview">
      <Typography variant="h6">生成された workflow.yaml</Typography>
      {workflowYaml ? (
        <CodeSnippet value={workflowYaml} language="yaml" />
      ) : (
        <Typography color="text.secondary">YAML が生成されるとここに表示されます。</Typography>
      )}
    </Paper>
  );
}

function AnalysisCard({ analysis }: { analysis?: WorkflowAnalysisMetadata }) {
  return (
    <Paper variant="outlined" sx={{ p: 3, display: "grid", gap: 2 }} data-testid="llm-analysis-card">
      <Typography variant="h6">要件分析</Typography>
      {analysis ? (
        <>
          {analysis.summary && (
            <Typography variant="body1" fontWeight={600}>
              {analysis.summary}
            </Typography>
          )}
          {analysis.primaryGoal && (
            <Typography variant="body2" color="text.secondary">
              主要目的: {analysis.primaryGoal}
            </Typography>
          )}
          <RequirementList requirements={analysis.requirements} />
        </>
      ) : (
        <Typography color="text.secondary">分析結果が生成されるとここに表示されます。</Typography>
      )}
    </Paper>
  );
}

function RequirementList({ requirements }: { requirements: RequirementMetadata[] }) {
  if (!requirements.length) {
    return (
      <Typography color="text.secondary">LLM からの要件分解結果はまだありません。</Typography>
    );
  }

  return (
    <Stack spacing={2}>
      {requirements.map((requirement) => (
        <Box
          key={requirement.id}
          sx={{
            borderRadius: 1,
            bgcolor: "#f5f7fb",
            p: 2,
            border: "1px solid",
            borderColor: "divider",
          }}
        >
          <Typography variant="subtitle2" fontWeight={600}>
            {requirement.id} · {requirement.title}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            カテゴリ: {requirement.category}
          </Typography>
          <Typography variant="body2" sx={{ mt: 1 }}>
            {requirement.description}
          </Typography>
          {requirement.acceptanceCriteria.length > 0 && (
            <List dense sx={{ listStyle: "disc", pl: 3 }}>
              {requirement.acceptanceCriteria.map((criteria, index) => (
                <ListItem key={index} sx={{ display: "list-item", pl: 0 }}>
                  <ListItemText primary={criteria} primaryTypographyProps={{ variant: "body2" }} />
                </ListItem>
              ))}
            </List>
          )}
        </Box>
      ))}
    </Stack>
  );
}

function ArchitectureCard({ architecture }: { architecture?: WorkflowArchitectureMetadata }) {
  return (
    <Paper variant="outlined" sx={{ p: 3, display: "grid", gap: 2 }} data-testid="llm-architecture-card">
      <Typography variant="h6">アーキテクチャ設計</Typography>
      {architecture ? (
        <Stack spacing={2}>
          {Object.keys(architecture.infoSection).length > 0 && (
            <Box>
              <Typography variant="subtitle2">info セクション</Typography>
              <KeyValueList data={architecture.infoSection} />
            </Box>
          )}
          {Object.keys(architecture.workflowsSection).length > 0 && (
            <Box>
              <Typography variant="subtitle2">workflows セクション</Typography>
              <Stack spacing={1}>
                {Object.entries(architecture.workflowsSection).map(([name, config]) => (
                  <Box key={name} sx={{ border: "1px solid", borderColor: "divider", borderRadius: 1, p: 2 }}>
                    <Typography variant="subtitle2" fontWeight={600}>
                      {name}
                    </Typography>
                    <KeyValueList data={config} />
                  </Box>
                ))}
              </Stack>
            </Box>
          )}
          {architecture.uiStructure && (
            <Box>
              <Typography variant="subtitle2">ui セクション</Typography>
              <CodeSnippet value={JSON.stringify(architecture.uiStructure, null, 2)} language="json" />
            </Box>
          )}
          {architecture.pipelineStructure && architecture.pipelineStructure.length > 0 && (
            <Box>
              <Typography variant="subtitle2">pipeline セクション</Typography>
              <CodeSnippet value={JSON.stringify(architecture.pipelineStructure, null, 2)} language="json" />
            </Box>
          )}
          {architecture.rationale && (
            <Typography variant="body2" color="text.secondary">
              設計意図: {architecture.rationale}
            </Typography>
          )}
        </Stack>
      ) : (
        <Typography color="text.secondary">アーキテクチャ設計が生成されるとここに表示されます。</Typography>
      )}
    </Paper>
  );
}

function KeyValueList({ data }: { data: Record<string, unknown> }) {
  const entries = Object.entries(data);
  if (entries.length === 0) {
    return <Typography color="text.secondary">値が定義されていません。</Typography>;
  }

  return (
    <List dense>
      {entries.map(([key, value]) => (
        <ListItem key={key} sx={{ alignItems: "flex-start" }}>
          <ListItemText
            primaryTypographyProps={{ variant: "body2", fontWeight: 600 }}
            secondaryTypographyProps={{ variant: "body2" }}
            primary={key}
            secondary={formatValue(value)}
          />
        </ListItem>
      ))}
    </List>
  );
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "未設定";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return JSON.stringify(value, null, 2);
}

function ValidationCard({ validation }: { validation?: WorkflowValidationMetadata }) {
  return (
    <Paper variant="outlined" sx={{ p: 3, display: "grid", gap: 2 }} data-testid="llm-validation-card">
      <Typography variant="h6">バリデーション結果</Typography>
      {validation ? (
        <Stack spacing={2}>
          <Alert severity={validation.valid ? "success" : "warning"}>
            {validation.valid ? "YAML の検証に成功しました。" : "検証中に問題が見つかりました。"}
          </Alert>
          <Stack direction="row" spacing={1} flexWrap="wrap">
            {validation.schemaValid !== undefined && (
              <Chip
                label={`スキーマ検証: ${validation.schemaValid ? "成功" : "失敗"}`}
                color={validation.schemaValid ? "success" : "error"}
                variant={validation.schemaValid ? "filled" : "outlined"}
              />
            )}
            {validation.llmValid !== undefined && (
              <Chip
                label={`LLM 検証: ${validation.llmValid ? "成功" : "失敗"}`}
                color={validation.llmValid ? "success" : "error"}
                variant={validation.llmValid ? "filled" : "outlined"}
              />
            )}
          </Stack>
          {validation.allErrors.length > 0 && (
            <Box>
              <Typography variant="subtitle2">検出されたエラー</Typography>
              <List dense sx={{ listStyle: "disc", pl: 3 }}>
                {validation.allErrors.map((error, index) => (
                  <ListItem key={index} sx={{ display: "list-item", pl: 0 }}>
                    <ListItemText primary={error} primaryTypographyProps={{ variant: "body2" }} />
                  </ListItem>
                ))}
              </List>
            </Box>
          )}
          {validation.suggestions.length > 0 && (
            <Box>
              <Typography variant="subtitle2">改善の提案</Typography>
              <List dense sx={{ listStyle: "disc", pl: 3 }}>
                {validation.suggestions.map((suggestion, index) => (
                  <ListItem key={index} sx={{ display: "list-item", pl: 0 }}>
                    <ListItemText primary={suggestion} primaryTypographyProps={{ variant: "body2" }} />
                  </ListItem>
                ))}
              </List>
            </Box>
          )}
        </Stack>
      ) : (
        <Typography color="text.secondary">バリデーションが完了すると結果が表示されます。</Typography>
      )}
    </Paper>
  );
}
