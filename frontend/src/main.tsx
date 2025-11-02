import React from "react";
import ReactDOM from "react-dom/client";
import AppGenerator from "./AppGenerator";
import { CssBaseline, ThemeProvider, createTheme } from "@mui/material";

const theme = createTheme({
  palette: {
    primary: {
      main: "#1976d2"
    },
    secondary: {
      main: "#009688"
    }
  },
  shape: {
    borderRadius: 12
  }
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AppGenerator />
    </ThemeProvider>
  </React.StrictMode>
);

