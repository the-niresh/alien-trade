import { defineConfig } from "@trigger.dev/sdk/v3";

// TRIGGER_PROJECT_REF comes from the Trigger.dev dashboard (proj_...).
export default defineConfig({
  project: process.env.TRIGGER_PROJECT_REF ?? "proj_alien_trade",
  dirs: ["./src"],
  maxDuration: 300,
  retries: {
    enabledInDev: true,
    default: {
      maxAttempts: 3,            // retry 3× then dead-letter + alert
      factor: 2,
      minTimeoutInMs: 1000,
      maxTimeoutInMs: 30000,
      randomize: true,
    },
  },
});
