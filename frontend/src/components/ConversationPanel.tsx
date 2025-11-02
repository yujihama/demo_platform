import type { ReactNode } from "react";

import { Avatar, Box, Paper, Stack, Typography } from "@mui/material";

export type ConversationMessage = {
  id: string;
  role: "user" | "agent";
  title: string;
  content: ReactNode;
  subtitle?: string;
};

type Props = {
  messages: ConversationMessage[];
};

const ROLE_CONFIG: Record<ConversationMessage["role"], { avatar: string; color: string }> = {
  user: { avatar: "私", color: "primary.main" },
  agent: { avatar: "AI", color: "info.main" }
};

export function ConversationPanel({ messages }: Props) {
  return (
    <Paper variant="outlined" sx={{ p: 3, height: "100%" }} aria-label="エージェントとの対話">
      <Stack spacing={2} sx={{ height: "100%" }}>
        <Typography variant="h6" component="h2">
          エージェントとの対話
        </Typography>

        {messages.length === 0 && (
          <Typography variant="body2" color="text.secondary">
            プロンプトを送信すると、ここに要件分析や設計内容が表示されます。
          </Typography>
        )}

        <Stack spacing={2} sx={{ flexGrow: 1, overflowY: "auto", pr: 1 }}>
          {messages.map((message) => {
            const role = ROLE_CONFIG[message.role];
            return (
              <Box
                key={message.id}
                sx={{
                  display: "flex",
                  flexDirection: message.role === "user" ? "row-reverse" : "row",
                  alignItems: "flex-start",
                  gap: 2
                }}
              >
                <Avatar sx={{ bgcolor: role.color }}>{role.avatar}</Avatar>
                <Paper
                  variant="outlined"
                  sx={{
                    p: 2,
                    bgcolor: message.role === "user" ? "primary.light" : "background.default",
                    maxWidth: "100%",
                    flexGrow: 1
                  }}
                >
                  <Stack spacing={1}>
                    <Typography variant="subtitle2" color="text.secondary">
                      {message.title}
                    </Typography>
                    {message.subtitle && (
                      <Typography variant="body2" color="text.secondary">
                        {message.subtitle}
                      </Typography>
                    )}
                    <Box sx={{ "& pre": { m: 0, whiteSpace: "pre-wrap", wordBreak: "break-word" } }}>{message.content}</Box>
                  </Stack>
                </Paper>
              </Box>
            );
          })}
        </Stack>
      </Stack>
    </Paper>
  );
}
