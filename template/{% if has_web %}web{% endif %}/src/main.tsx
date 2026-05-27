import "./index.css";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { ThemeProvider } from "next-themes";
import App from "./App";
import { Toaster } from "@/components/ui/sonner";
import { initOtel } from "./otel";

// Initialise browser OTel SDK before React mounts so instrumentation is active
// before the first fetch() can fire.  Inert (no-op) unless
// VITE_OTEL_EXPORTER_OTLP_ENDPOINT is set at build time.
initOtel();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      <App />
      <Toaster />
    </ThemeProvider>
  </StrictMode>
);
