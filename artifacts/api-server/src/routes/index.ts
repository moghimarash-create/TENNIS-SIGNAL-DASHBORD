import { Router, type IRouter } from "express";
import healthRouter from "./health";
import stepsRouter from "./steps";
import presetRouter from "./preset";

const router: IRouter = Router();

router.use(healthRouter);
router.use(stepsRouter);
router.use(presetRouter);

export default router;
