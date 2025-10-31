import { Alert, Button } from "@mui/material";

type Props = {
  message: string;
  onRetry?: () => void;
};

export function ErrorBanner({ message, onRetry }: Props) {
  return (
    <Alert
      severity="error"
      action={
        onRetry ? (
          <Button color="inherit" size="small" onClick={onRetry}>
            再試行
          </Button>
        ) : undefined
      }
    >
      {message}
    </Alert>
  );
}

