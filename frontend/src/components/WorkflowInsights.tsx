import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Chip,
  Divider,
  List,
  ListItem,
  ListItemText,
  Paper,
  Stack,
  Typography
} from "@mui/material";

import type {
  RequirementItem,
  WorkflowAnalysisMetadata,
  WorkflowArchitectureMetadata,
  WorkflowValidationMetadata
} from "../types";

type Props = {
  analysis?: WorkflowAnalysisMetadata;
  architecture?: WorkflowArchitectureMetadata;
  validation?: WorkflowValidationMetadata;
};

function renderRequirement(requirement: RequirementItem) {
  return (
    <ListItem key={requirement.id} alignItems="flex-start" sx={{ pl: 0 }}>
      <ListItemText
        primary={`${requirement.id}: ${requirement.title}`}
        secondary={
          <Stack spacing={1}>
            <Typography variant="body2" color="text.secondary">
              {requirement.description}
            </Typography>
            {requirement.acceptance_criteria.length > 0 && (
              <Stack component="ul" sx={{ pl: 3, m: 0 }}>
                {requirement.acceptance_criteria.map((item) => (
                  <Typography component="li" variant="body2" key={item}>
                    {item}
                  </Typography>
                ))}
              </Stack>
            )}
          </Stack>
        }
      />
    </ListItem>
  );
}

function renderJson(label: string, value: unknown) {
  return (
    <Stack spacing={1}>
      <Typography variant="subtitle2" color="text.secondary">
        {label}
      </Typography>
      <Typography
        component="pre"
        sx={{
          bgcolor: "grey.50",
          borderRadius: 1,
          border: "1px solid",
          borderColor: "divider",
          p: 2,
          fontFamily: "'Fira Code', monospace",
          fontSize: 13,
          whiteSpace: "pre-wrap",
          wordBreak: "break-word"
        }}
      >
        {JSON.stringify(value, null, 2)}
      </Typography>
    </Stack>
  );
}

export function WorkflowInsights({ analysis, architecture, validation }: Props) {
  const hasInsights = analysis || architecture || validation;

  return (
    <Paper variant="outlined" sx={{ p: 3 }} aria-label="生成内容のサマリー">
      <Stack spacing={2}>
        <Typography variant="h6" component="h2">
          生成内容のサマリー
        </Typography>

        {!hasInsights && (
          <Typography variant="body2" color="text.secondary">
            生成が完了すると、ここに要件分析・設計・検証結果が表示されます。
          </Typography>
        )}

        {analysis && (
          <Accordion defaultExpanded disableGutters>
            <AccordionSummary expandIcon={<ExpandMoreIcon />} aria-controls="analysis-content">
              <Typography variant="subtitle1">要件分析結果</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Stack spacing={2}>
                <Typography variant="body1">{analysis.summary}</Typography>
                <Typography variant="body2" color="text.secondary">
                  主要な目的: {analysis.primary_goal}
                </Typography>
                <Divider />
                <Typography variant="subtitle2">抽出された要件</Typography>
                <List disablePadding>
                  {analysis.requirements.map((requirement) => renderRequirement(requirement))}
                </List>
              </Stack>
            </AccordionDetails>
          </Accordion>
        )}

        {architecture && (
          <Accordion defaultExpanded disableGutters>
            <AccordionSummary expandIcon={<ExpandMoreIcon />} aria-controls="architecture-content">
              <Typography variant="subtitle1">アーキテクチャ設計</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Stack spacing={2}>
                <Typography variant="body2" color="text.secondary">
                  {architecture.rationale}
                </Typography>
                {renderJson("info", architecture.info_section)}
                {renderJson("workflows", architecture.workflows_section)}
                {renderJson("ui", architecture.ui_structure)}
                {renderJson("pipeline", architecture.pipeline_structure)}
              </Stack>
            </AccordionDetails>
          </Accordion>
        )}

        {validation && (
          <Accordion defaultExpanded disableGutters>
            <AccordionSummary expandIcon={<ExpandMoreIcon />} aria-controls="validation-content">
              <Stack direction="row" alignItems="center" spacing={1}>
                <Typography variant="subtitle1">検証結果</Typography>
                <Chip label={validation.valid ? "合格" : "要修正"} color={validation.valid ? "success" : "error"} size="small" />
              </Stack>
            </AccordionSummary>
            <AccordionDetails>
              <Stack spacing={2}>
                <Typography variant="body2" color="text.secondary">
                  スキーマ検証: {validation.schema_valid ? "成功" : "失敗"}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  LLM 検証: {validation.llm_valid ? "成功" : "失敗"}
                </Typography>
                {validation.schema_errors.length > 0 && renderJson("スキーマエラー", validation.schema_errors)}
                {validation.llm_errors.length > 0 && renderJson("LLM エラー", validation.llm_errors)}
                {validation.suggestions.length > 0 && renderJson("改善提案", validation.suggestions)}
              </Stack>
            </AccordionDetails>
          </Accordion>
        )}
      </Stack>
    </Paper>
  );
}
