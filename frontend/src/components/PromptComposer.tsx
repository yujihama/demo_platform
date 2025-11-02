import type { FormEvent } from "react";

import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Box,
  Button,
  Paper,
  Stack,
  TextField,
  Typography
} from "@mui/material";

import { SamplePrompt } from "./SamplePrompt";

export interface PromptComposerValues {
  prompt: string;
  userId: string;
  projectId: string;
  projectName: string;
  description: string;
}

export interface PromptComposerErrors {
  prompt?: string;
  userId?: string;
  projectId?: string;
  projectName?: string;
  description?: string;
}

type Props = {
  values: PromptComposerValues;
  errors: PromptComposerErrors;
  onChange: <K extends keyof PromptComposerValues>(field: K, value: PromptComposerValues[K]) => void;
  onSubmit: () => void;
  onReset: () => void;
  submitting: boolean;
  disabled?: boolean;
};

export function PromptComposer({ values, errors, onChange, onSubmit, onReset, submitting, disabled }: Props) {
  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    onSubmit();
  };

  const isDisabled = submitting || Boolean(disabled);

  return (
    <Paper component="form" elevation={0} onSubmit={handleSubmit} sx={{ p: 3 }}>
      <Stack spacing={2}>
        <Box>
          <Typography variant="h6" component="h2" gutterBottom>
            要件プロンプト
          </Typography>
          <Typography variant="body2" color="text.secondary">
            LLM に実装してほしいアプリの要件を自然言語で入力すると、宣言的な workflow.yaml を生成します。
          </Typography>
        </Box>

        <TextField
          label="要件プロンプト"
          aria-label="要件プロンプト"
          multiline
          minRows={5}
          value={values.prompt}
          onChange={(event) => onChange("prompt", event.target.value)}
          disabled={isDisabled}
          error={Boolean(errors.prompt)}
          helperText={errors.prompt ?? "例: 請求書をアップロードし、検証結果をダッシュボードで確認できるアプリを作って"}
        />

        <SamplePrompt />

        <Accordion disableGutters>
          <AccordionSummary expandIcon={<ExpandMoreIcon />} aria-controls="advanced-settings" id="advanced-settings-header">
            <Typography variant="subtitle1">詳細設定</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Stack spacing={2}>
              <TextField
                label="ユーザー ID"
                value={values.userId}
                onChange={(event) => onChange("userId", event.target.value)}
                disabled={isDisabled}
                error={Boolean(errors.userId)}
                helperText={errors.userId}
              />
              <TextField
                label="プロジェクト ID"
                value={values.projectId}
                onChange={(event) => onChange("projectId", event.target.value)}
                disabled={isDisabled}
                error={Boolean(errors.projectId)}
                helperText={errors.projectId}
              />
              <TextField
                label="プロジェクト名"
                value={values.projectName}
                onChange={(event) => onChange("projectName", event.target.value)}
                disabled={isDisabled}
                error={Boolean(errors.projectName)}
                helperText={errors.projectName}
              />
              <TextField
                label="プロジェクト概要"
                multiline
                minRows={2}
                value={values.description}
                onChange={(event) => onChange("description", event.target.value)}
                disabled={isDisabled}
                error={Boolean(errors.description)}
                helperText={errors.description}
              />
            </Stack>
          </AccordionDetails>
        </Accordion>

        <Box sx={{ display: "flex", gap: 2, justifyContent: "flex-end" }}>
          <Button type="button" variant="outlined" color="secondary" onClick={onReset} disabled={submitting}>
            入力をリセット
          </Button>
          <Button type="submit" variant="contained" disabled={isDisabled}>
            生成を開始
          </Button>
        </Box>
      </Stack>
    </Paper>
  );
}
