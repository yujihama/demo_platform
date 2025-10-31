import { useMemo } from "react";
import {
  Box,
  Button,
  Checkbox,
  CircularProgress,
  FormControlLabel,
  Grid,
  TextField,
  Typography
} from "@mui/material";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import type { GenerationRequest } from "../types";
import { SamplePrompt } from "./SamplePrompt";

const schema = z.object({
  user_id: z.string().min(3, "3文字以上で入力してください"),
  project_id: z.string().min(3, "3文字以上で入力してください"),
  project_name: z.string().min(3, "3文字以上で入力してください"),
  description: z.string().min(10, "10文字以上で入力してください"),
  mock_spec_id: z.string().default("invoice-verification"),
  include_playwright: z.boolean().default(true),
  include_docker: z.boolean().default(true),
  include_logging: z.boolean().default(true)
});

type FormValues = z.infer<typeof schema>;

type Props = {
  onSubmit: (payload: GenerationRequest) => void;
  loading: boolean;
  error?: string | null;
};

const defaultValues: FormValues = {
  user_id: "demo-user",
  project_id: "invoice-verification-mvp",
  project_name: "Invoice Verification Assistant",
  description: "請求書の検証と承認フローを自動化するアプリ",
  mock_spec_id: "invoice-verification",
  include_playwright: true,
  include_docker: true,
  include_logging: true
};

export function StepRequirements({ onSubmit, loading, error }: Props) {
  const {
    register,
    handleSubmit,
    formState: { errors }
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues
  });

  const helper = useMemo(
    () => ({
      userId: errors.user_id?.message,
      projectId: errors.project_id?.message,
      projectName: errors.project_name?.message,
      description: errors.description?.message
    }),
    [errors]
  );

  const submit = handleSubmit((values) => {
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
      }
    };
    onSubmit(payload);
  });

  return (
    <Box component="form" onSubmit={submit} sx={{ display: "grid", gap: 3 }}>
      <input type="hidden" value={defaultValues.mock_spec_id} {...register("mock_spec_id")} />
      <Typography variant="body1">
        Phase 2 では自然言語で要件を記述することで、LLMエージェントが自動的にアプリケーション仕様を生成します。基本情報とアプリの概要を入力し「生成を開始」を押してください。
      </Typography>

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
        label="アプリの概要（自然言語で記述）"
        multiline
        minRows={5}
        placeholder="例: 請求書をアップロードして、金額や日付などを検証し、問題があればエラーを表示するアプリを作成したい"
        disabled={loading}
        error={Boolean(helper.description)}
        helperText={helper.description || "自然言語でアプリの要件を詳しく記述してください"}
        {...register("description")}
      />

      <SamplePrompt />

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

