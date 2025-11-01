import { useEffect, useMemo } from "react";
import {
  Box,
  Button,
  Checkbox,
  CircularProgress,
  Divider,
  FormControlLabel,
  Grid,
  Switch,
  TextField,
  Typography
} from "@mui/material";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import type { FeaturesConfig, GenerationRequest } from "../types";
import { SamplePrompt } from "./SamplePrompt";

const schema = z.object({
  user_id: z.string().min(3, "3文字以上で入力してください"),
  project_id: z.string().min(3, "3文字以上で入力してください"),
  project_name: z.string().min(3, "3文字以上で入力してください"),
  description: z.string().min(10, "10文字以上で入力してください"),
  requirements_prompt: z.string().min(10, "10文字以上で入力してください"),
  mock_spec_id: z.string().default("invoice-verification"),
  include_playwright: z.boolean().default(true),
  include_docker: z.boolean().default(true),
  include_logging: z.boolean().default(true),
  use_mock: z.boolean().optional()
});

type FormValues = z.infer<typeof schema>;

type Props = {
  onSubmit: (payload: GenerationRequest) => void;
  loading: boolean;
  error?: string | null;
  features: FeaturesConfig | null;
};

const defaultValues: FormValues = {
  user_id: "demo-user",
  project_id: "invoice-verification-mvp",
  project_name: "Invoice Verification Assistant",
  description: "請求書の検証と承認フローを自動化するアプリ",
  requirements_prompt: "経理担当者がアップロードした請求書を自動検証し、重複と金額閾値をチェックして承認フローに渡す React + FastAPI アプリを生成して",
  mock_spec_id: "invoice-verification",
  include_playwright: true,
  include_docker: true,
  include_logging: true,
  use_mock: true
};

export function StepRequirements({ onSubmit, loading, error, features }: Props) {
  const {
    register,
    handleSubmit,
    control,
    setValue,
    formState: { errors }
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues
  });

  useEffect(() => {
    if (features) {
      setValue("use_mock", features.agents.use_mock);
    }
  }, [features, setValue]);

  const helper = useMemo(
    () => ({
      userId: errors.user_id?.message,
      projectId: errors.project_id?.message,
      projectName: errors.project_name?.message,
      description: errors.description?.message,
      requirementsPrompt: errors.requirements_prompt?.message
    }),
    [errors]
  );

  const submit = handleSubmit((values) => {
    const allowToggle = features?.agents.allow_llm_toggle ?? false;
    const resolvedUseMock = allowToggle ? values.use_mock : features?.agents.use_mock ?? true;
    const payload: GenerationRequest = {
      user_id: values.user_id,
      project_id: values.project_id,
      project_name: values.project_name,
      description: values.description,
      mock_spec_id: values.mock_spec_id,
      options: {
        include_playwright: values.include_playwright,
        include_docker: values.include_docker,
        include_logging: values.include_logging
      },
      requirements_prompt: values.requirements_prompt.trim(),
      use_mock: resolvedUseMock
    };
    onSubmit(payload);
  });

  const allowToggle = features?.agents.allow_llm_toggle ?? false;

  return (
    <Box component="form" onSubmit={submit} sx={{ display: "grid", gap: 3 }}>
      <input type="hidden" value={defaultValues.mock_spec_id} {...register("mock_spec_id")} />
      <Typography variant="body1">
        自然言語でアプリの要件を入力すると、LLM が仕様を分解して成果物を生成します。モックモードでは従来の固定仕様を利用します。
      </Typography>

      {allowToggle && (
        <Controller
          name="use_mock"
          control={control}
          render={({ field }) => (
            <FormControlLabel
              control={<Switch {...field} checked={field.value ?? (features?.agents.use_mock ?? true)} disabled={loading} />}
              label={field.value ? "モックモード" : "LLMモード"}
            />
          )}
        />
      )}

      <TextField
        label="要件プロンプト"
        multiline
        minRows={5}
        disabled={loading}
        error={Boolean(helper.requirementsPrompt)}
        helperText={helper.requirementsPrompt ?? "例: 請求書をアップロードして検証結果を表示するアプリを生成して"}
        {...register("requirements_prompt")}
      />

      <SamplePrompt />

      <Divider sx={{ my: 1 }} />

      <Typography variant="subtitle1">生成設定</Typography>

      <Grid container spacing={2}>
        <Grid item xs={12} md={6}>
          <TextField
            label="ユーザー ID"
            fullWidth
            disabled={loading}
            error={Boolean(helper.userId)}
            helperText={helper.userId}
            {...register("user_id")}
          />
        </Grid>
        <Grid item xs={12} md={6}>
          <TextField
            label="プロジェクト ID"
            fullWidth
            disabled={loading}
            error={Boolean(helper.projectId)}
            helperText={helper.projectId}
            {...register("project_id")}
          />
        </Grid>
      </Grid>

      <TextField
        label="プロジェクト名"
        fullWidth
        disabled={loading}
        error={Boolean(helper.projectName)}
        helperText={helper.projectName}
        {...register("project_name")}
      />

      <TextField
        label="プロジェクト概要"
        multiline
        minRows={2}
        disabled={loading}
        error={Boolean(helper.description)}
        helperText={helper.description}
        {...register("description")}
      />

      <Box sx={{ display: "flex", gap: 2 }}>
        <FormControlLabel
          control={<Checkbox defaultChecked disabled={loading} {...register("include_playwright")} />}
          label="Playwright テストを含める"
        />
        <FormControlLabel
          control={<Checkbox defaultChecked disabled={loading} {...register("include_docker")} />}
          label="Docker 構成を含める"
        />
        <FormControlLabel
          control={<Checkbox defaultChecked disabled={loading} {...register("include_logging")} />}
          label="ロギング設定を含める"
        />
      </Box>

      {error && (
        <Typography color="error" role="alert">
          {error}
        </Typography>
      )}

      <Box sx={{ display: "flex", justifyContent: "flex-end" }}>
        <Button type="submit" variant="contained" size="large" disabled={loading} startIcon={loading ? <CircularProgress size={18} /> : null}>
          {loading ? "送信中" : "生成を開始"}
        </Button>
      </Box>
    </Box>
  );
}

