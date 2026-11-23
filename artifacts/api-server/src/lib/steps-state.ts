import { promises as fs } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const DATA_DIR = path.resolve(__dirname, "../../data");
const STATE_FILE = path.join(DATA_DIR, "dashboard_state.json");
const LOGS_DIR = path.resolve(__dirname, "../../logs");

export type StepStatus = "idle" | "running" | "success" | "error";

export type LastRun = {
  status: StepStatus;
  finishedAt: string | null;
  durationMs: number | null;
  rowsWritten: number | null;
  message: string | null;
  error: string | null;
};

type StateFile = {
  steps: Record<string, LastRun>;
};

const DEFAULT_LAST_RUN: LastRun = {
  status: "idle",
  finishedAt: null,
  durationMs: null,
  rowsWritten: null,
  message: null,
  error: null,
};

async function ensureDirs(): Promise<void> {
  await fs.mkdir(DATA_DIR, { recursive: true });
  await fs.mkdir(LOGS_DIR, { recursive: true });
}

async function readStateUnlocked(): Promise<StateFile> {
  await ensureDirs();
  try {
    const raw = await fs.readFile(STATE_FILE, "utf-8");
    return JSON.parse(raw) as StateFile;
  } catch {
    return { steps: {} };
  }
}

async function writeStateAtomic(state: StateFile): Promise<void> {
  await ensureDirs();
  const tmp = STATE_FILE + ".tmp";
  await fs.writeFile(tmp, JSON.stringify(state, null, 2), "utf-8");
  await fs.rename(tmp, STATE_FILE);
}

// Serialize all state file mutations to avoid lost updates from concurrent runs.
let stateChain: Promise<unknown> = Promise.resolve();
function withStateLock<T>(fn: () => Promise<T>): Promise<T> {
  const next = stateChain.then(fn, fn);
  stateChain = next.catch(() => undefined);
  return next;
}

export async function getLastRun(stepId: number): Promise<LastRun> {
  return withStateLock(async () => {
    const state = await readStateUnlocked();
    return state.steps[String(stepId)] ?? DEFAULT_LAST_RUN;
  });
}

export async function setLastRun(
  stepId: number,
  lastRun: LastRun,
): Promise<void> {
  await withStateLock(async () => {
    const state = await readStateUnlocked();
    state.steps[String(stepId)] = lastRun;
    await writeStateAtomic(state);
  });
}

export function logFilePath(stepId: number): string {
  return path.join(LOGS_DIR, `step${stepId}.log`);
}

export async function readLogs(stepId: number, maxLines = 500): Promise<string[]> {
  await ensureDirs();
  try {
    const raw = await fs.readFile(logFilePath(stepId), "utf-8");
    const lines = raw.split(/\r?\n/);
    return lines.slice(-maxLines);
  } catch {
    return [];
  }
}

export async function writeLogs(stepId: number, content: string): Promise<void> {
  await ensureDirs();
  await fs.writeFile(logFilePath(stepId), content, "utf-8");
}

// In-process locks to prevent concurrent runs of the same step.
const running = new Set<number>();
let pipelineRunning = false;

export function isRunning(stepId: number): boolean {
  return running.has(stepId);
}
export function markRunning(stepId: number): void {
  running.add(stepId);
}
export function markFinished(stepId: number): void {
  running.delete(stepId);
}
export function isPipelineRunning(): boolean {
  return pipelineRunning;
}
export function setPipelineRunning(v: boolean): void {
  pipelineRunning = v;
}
