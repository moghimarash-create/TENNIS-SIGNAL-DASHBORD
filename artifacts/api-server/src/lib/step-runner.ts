import { spawn } from "node:child_process";
import { logger } from "./logger";
import { getStep, type StepDef } from "./steps-config";
import {
  getLastRun,
  isRunning,
  markFinished,
  markRunning,
  setLastRun,
  writeLogs,
  type LastRun,
} from "./steps-state";

export type RunOutcome = {
  ok: boolean;
  lastRun: LastRun;
};

const RESULT_PREFIX = "__RESULT__ ";

type ScriptResult = {
  ok?: boolean;
  rowsWritten?: number | null;
  message?: string | null;
  error?: string | null;
};

export type RunStepOptions = {
  // Step 4 only: market codes to EXCLUDE (the ones the user unchecked). The
  // Python script runs the visible KEY-MATCH-* tabs minus this set, so when
  // undefined/empty all visible markets run and dynamic discovery is preserved.
  disabledMarkets?: string[];
};

// Build the full argv for a step, folding in any dynamic run options.
function buildArgs(step: StepDef, opts: RunStepOptions): string[] {
  const args = [...step.args];
  if (step.id === 4 && opts.disabledMarkets && opts.disabledMarkets.length > 0) {
    // Pass the excluded markets as a comma-separated flag. Omitted when empty
    // so Python falls back to running every visible market.
    args.push("--disabled-markets", opts.disabledMarkets.join(","));
  }
  return args;
}

function spawnStep(
  step: StepDef,
  opts: RunStepOptions,
): Promise<{
  exitCode: number;
  stdout: string;
  stderr: string;
  combined: string;
  parsed: ScriptResult | null;
}> {
  return new Promise((resolve) => {
    const child = spawn(step.command, buildArgs(step, opts), {
      env: process.env,
    });
    let stdout = "";
    let stderr = "";
    let combined = "";
    child.stdout.on("data", (d: Buffer) => {
      const s = d.toString();
      stdout += s;
      combined += s;
    });
    child.stderr.on("data", (d: Buffer) => {
      const s = d.toString();
      stderr += s;
      combined += s;
    });
    child.on("error", (err) => {
      const msg = `Failed to start subprocess: ${err.message}`;
      combined += msg + "\n";
      resolve({ exitCode: -1, stdout, stderr, combined, parsed: null });
    });
    child.on("close", (code) => {
      let parsed: ScriptResult | null = null;
      const lines = stdout.split(/\r?\n/).reverse();
      for (const line of lines) {
        if (line.startsWith(RESULT_PREFIX)) {
          try {
            parsed = JSON.parse(line.slice(RESULT_PREFIX.length)) as ScriptResult;
          } catch {
            // ignore
          }
          break;
        }
      }
      resolve({ exitCode: code ?? -1, stdout, stderr, combined, parsed });
    });
  });
}

export async function runStep(
  stepId: number,
  opts: RunStepOptions = {},
): Promise<RunOutcome> {
  const step = getStep(stepId);
  if (!step) {
    throw new Error(`Unknown step id: ${stepId}`);
  }
  if (isRunning(stepId)) {
    throw Object.assign(new Error("Step is already running"), { code: 409 });
  }
  markRunning(stepId);
  const startedAt = Date.now();
  try {
    logger.info({ stepId, name: step.name }, "Running step");
    const { exitCode, combined, parsed } = await spawnStep(step, opts);
    const durationMs = Date.now() - startedAt;
    const finishedAt = new Date().toISOString();
    await writeLogs(
      stepId,
      `# Step ${stepId} - ${step.name}\n# Started: ${new Date(startedAt).toISOString()}\n# Finished: ${finishedAt}\n# Exit code: ${exitCode}\n\n${combined}`,
    );

    const ok = exitCode === 0 && parsed?.ok !== false;
    const lastRun: LastRun = {
      status: ok ? "success" : "error",
      finishedAt,
      durationMs,
      rowsWritten: parsed?.rowsWritten ?? null,
      message: parsed?.message ?? null,
      error: ok
        ? null
        : parsed?.error ?? `Process exited with code ${exitCode}`,
    };
    await setLastRun(stepId, lastRun);
    return { ok, lastRun };
  } finally {
    markFinished(stepId);
  }
}

export async function getStatus(stepId: number): Promise<LastRun> {
  if (isRunning(stepId)) {
    return {
      status: "running",
      finishedAt: null,
      durationMs: null,
      rowsWritten: null,
      message: "Currently running...",
      error: null,
    };
  }
  return getLastRun(stepId);
}
