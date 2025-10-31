import { Alert, Button } from "@mui/material";

type Props = {
  message: string;
  details?: string[];
  onRetry?: () => void;
};

export function ErrorBanner({ message, details, onRetry }: Props) {
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
      {details && details.length > 0 && (
        <ul style={{ marginTop: 8, paddingLeft: 20 }}>
          {details.map((item, index) => (
            <li key={index}>{item}</li>
          ))}
        </ul>
      )}
    </Alert>
  );
}

