import { Router, type IRouter } from "express";
import {
  ListStepsResponse,
  RunStepParams,
  RunStepBody,
  RunStepResponse,
  RunAllStepsResponse,
  GetStepLogsParams,
  GetStepLogsResponse,
} from "@workspace/api-zod";
import { STEPS, getStep } from "../lib/steps-config";
import { getStatus, runStep } from "../lib/step-runner";
import {
  isPipelineRunning,
  isRunning,
  readLogs,
  setPipelineRunning,
} from "../lib/steps-state";

const IMPLEMENTED_STEPS = STEPS.filter((s) => s.implemented);

const router: IRouter = Router();

async function buildStepDto(stepId: number) {
  const step = getStep(stepId);
  if (!step) throw new Error(`Unknown step ${stepId}`);
  const lastRun = await getStatus(stepId);
  return {
    id: step.id,
    name: step.name,
    description: step.description,
    runtime: step.runtime,
    implemented: step.implemented,
    inputs: step.inputs,
    outputs: step.outputs,
    lastRun,
  };
}

router.get("/steps", async (_req, res): Promise<void> => {
  const steps = await Promise.all(STEPS.map((s) => buildStepDto(s.id)));
  res.json(ListStepsResponse.parse(steps));
});

router.post("/steps/:id/run", async (req, res): Promise<void> => {
  const params = RunStepParams.safeParse(req.params);
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }
  const { id } = params.data;
  if (!getStep(id)) {
    res.status(400).json({ error: `Unknown step id: ${id}` });
    return;
  }
  const body = RunStepBody.safeParse(req.body ?? {});
  if (!body.success) {
    res.status(400).json({ error: body.error.message });
    return;
  }
  if (isPipelineRunning()) {
    res.status(409).json({ error: "Pipeline run is in progress" });
    return;
  }
  if (isRunning(id)) {
    res.status(409).json({ error: "Step is already running" });
    return;
  }
  try {
    const outcome = await runStep(id, {
      disabledMarkets: body.data.disabledMarkets,
    });
    const dto = await buildStepDto(id);
    res.json(RunStepResponse.parse({ step: dto, ok: outcome.ok }));
  } catch (e) {
    const err = e as Error & { code?: number };
    req.log.error({ err }, "Step run failed");
    res
      .status(err.code === 409 ? 409 : 500)
      .json({ error: err.message ?? "Step run failed" });
  }
});

router.post("/steps/run-all", async (req, res): Promise<void> => {
  if (isPipelineRunning()) {
    res.status(409).json({ error: "Pipeline is already running" });
    return;
  }
  for (const s of STEPS) {
    if (isRunning(s.id)) {
      res.status(409).json({ error: `Step ${s.id} is already running` });
      return;
    }
  }
  if (IMPLEMENTED_STEPS.length === 0) {
    res
      .status(409)
      .json({ error: "No steps are implemented yet. Provide source code first." });
    return;
  }
  setPipelineRunning(true);
  const results: { step: unknown; ok: boolean }[] = [];
  let stoppedAtStep: number | null = null;
  let internalError: string | null = null;
  try {
    for (const s of STEPS) {
      const outcome = await runStep(s.id);
      const dto = await buildStepDto(s.id);
      results.push({ step: dto, ok: outcome.ok });
      if (!outcome.ok) {
        stoppedAtStep = s.id;
        break;
      }
    }
  } catch (e) {
    const err = e as Error;
    internalError = err.message ?? String(e);
    req.log.error({ err: e }, "Pipeline run failed");
    // Mark the last attempted step as the stopping point so callers see failure.
    if (stoppedAtStep === null && results.length > 0) {
      stoppedAtStep = (results[results.length - 1] as { step: { id: number } }).step.id;
    } else if (stoppedAtStep === null) {
      stoppedAtStep = STEPS[0]?.id ?? 1;
    }
  } finally {
    setPipelineRunning(false);
  }
  const ok =
    internalError === null &&
    stoppedAtStep === null &&
    results.every((r) => r.ok);
  res.json(
    RunAllStepsResponse.parse({
      ok,
      results,
      stoppedAtStep,
    }),
  );
});

router.get("/steps/:id/logs", async (req, res): Promise<void> => {
  const params = GetStepLogsParams.safeParse(req.params);
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }
  const { id } = params.data;
  const lines = await readLogs(id);
  res.json(GetStepLogsResponse.parse({ stepId: id, lines }));
});

export default router;
