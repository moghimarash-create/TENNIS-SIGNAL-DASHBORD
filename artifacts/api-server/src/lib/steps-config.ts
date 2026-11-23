import path from "node:path";
import { fileURLToPath } from "node:url";
import { TENNIS_TOURS } from "./tennis-config";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PYTHON_DIR = path.resolve(__dirname, "..", "python");

export type SheetLink = {
  label: string;
  spreadsheetId: string;
  tab?: string;
  url: string;
  market?: string;
};

export type StepDef = {
  id: number;
  name: string;
  description: string;
  runtime: "python" | "node";
  implemented: boolean;
  command: string;
  args: string[];
  inputs: SheetLink[];
  outputs: SheetLink[];
};

const DASHBORD_INPUT_ID = process.env.TENNIS_DASHBORD_INPUT_SHEET_ID ?? "";
const ASTRO_INPUT_ID = process.env.TENNIS_ASTRO_INPUT_SHEET_ID ?? "";
const ASTRO_HEADER_ID = process.env.TENNIS_ASTRO_HEADER_SHEET_ID ?? "";
const ASTRO_ASPECTS_ID = process.env.TENNIS_ASTRO_ASPECTS_SHEET_ID ?? "";
const RESULT_DEGREE_ID = process.env.TENNIS_RESULT_DEGREE_SHEET_ID ?? "";
const CALC_ID = process.env.TENNIS_CALC_SHEET_ID ?? "";

const sheetUrl = (id: string, tab?: string): string =>
  !id
    ? "#tennis-isolated-sheets-disabled"
    : tab
      ? `https://docs.google.com/spreadsheets/d/${id}/edit#gid=0&fvid=${encodeURIComponent(tab)}`
      : `https://docs.google.com/spreadsheets/d/${id}/edit`;

export const STEPS: StepDef[] = [
  {
    id: 1,
    name: `Tennis Tournament / City / Venue Geomantic Input (ATP DEG1=${TENNIS_TOURS.ATP.deg1} • WTA DEG1=${TENNIS_TOURS.WTA.deg1})`,
    description:
      "100% Astro-Gematria Tournament/City/Venue base engine (NO player birthdates): ATP Gematria 481 -> DEG1=121 (1° LEO • FIRE), WTA Gematria 407 -> DEG1=47 (17° TAURUS • EARTH). Auto-writing to live NBA/NHL Google Sheets is strictly disabled.",
    runtime: "python",
    implemented: true,
    command: "python",
    args: [path.join(PYTHON_DIR, "step1_geomantic.py")],
    inputs: [
      {
        label: "TENNIS-TOURNAMENT-GEOMANTIC-INPUT (Isolated • Auto-Write Disabled)",
        spreadsheetId: DASHBORD_INPUT_ID,
        tab: "Sheet1",
        url: sheetUrl(DASHBORD_INPUT_ID),
      },
    ],
    outputs: [
      {
        label: "TENNIS-Astro_Input (Data • Isolated)",
        spreadsheetId: ASTRO_INPUT_ID,
        tab: "Data",
        url: sheetUrl(ASTRO_INPUT_ID, "Data"),
      },
      {
        label: "TENNIS-Astro_Header_Input (Sheet1 • Isolated)",
        spreadsheetId: ASTRO_HEADER_ID,
        tab: "Sheet1",
        url: sheetUrl(ASTRO_HEADER_ID, "Sheet1"),
      },
    ],
  },
  {
    id: 2,
    name: "Tennis Match-Sky Planetary Aspects (pyswisseph @ Match Timestamp & Court Coordinates)",
    description:
      "Computes Swiss Ephemeris (pyswisseph) planetary aspects for ATP (DEG1=121, 1° LEO) and WTA (DEG1=47, 17° TAURUS) at exact match start time and tournament city/venue coordinates.",
    runtime: "python",
    implemented: true,
    command: "python",
    args: [path.join(PYTHON_DIR, "step2_astro_aspects.py")],
    inputs: [
      {
        label: "TENNIS-Astro_Input (Data)",
        spreadsheetId: ASTRO_INPUT_ID,
        tab: "Data",
        url: sheetUrl(ASTRO_INPUT_ID, "Data"),
      },
    ],
    outputs: [
      {
        label: "TENNIS-Astro_Aspects (Sheet1)",
        spreadsheetId: ASTRO_ASPECTS_ID,
        tab: "Sheet1",
        url: sheetUrl(ASTRO_ASPECTS_ID, "Sheet1"),
      },
    ],
  },
  {
    id: 3,
    name: "Tennis Result Degree & 36-Decan / Chaldean Node Builder",
    description:
      "Evaluates Result Degrees, 22 Arcana HOT/COLD & MOIST/DRY qualities, 36 Decans, Golden Dawn & Chaldean Rulers for Tournament + City + Court base power.",
    runtime: "python",
    implemented: true,
    command: "python",
    args: [path.join(PYTHON_DIR, "step3_result_degree.py")],
    inputs: [
      {
        label: "TENNIS-Astro_Aspects (Sheet1)",
        spreadsheetId: ASTRO_ASPECTS_ID,
        tab: "Sheet1",
        url: sheetUrl(ASTRO_ASPECTS_ID, "Sheet1"),
      },
    ],
    outputs: [
      {
        label: "TENNIS-Result-Degree :: Node_Output",
        spreadsheetId: RESULT_DEGREE_ID,
        tab: "Node_Output",
        url: sheetUrl(RESULT_DEGREE_ID, "Node_Output"),
      },
    ],
  },
  {
    id: 4,
    name: "Tennis Tournament/Venue Base Power & Match Predictions Builder",
    description:
      "Builds deterministic Sheet1, Sheet3, and Match_Predictions for ATP (KXATPMATCH • DEG1=121) & WTA (KXWTAMATCH • DEG1=47) completely isolated from NBA/NHL sheets.",
    runtime: "python",
    implemented: true,
    command: "python",
    args: [path.join(PYTHON_DIR, "step4_winner_prediction.py")],
    inputs: [
      {
        label: "TENNIS-Result-Degree :: Node_Output",
        spreadsheetId: RESULT_DEGREE_ID,
        tab: "Node_Output",
        url: sheetUrl(RESULT_DEGREE_ID, "Node_Output"),
      },
    ],
    outputs: [
      {
        label: "TENNIS-Calculation :: Match_Predictions (Isolated)",
        spreadsheetId: CALC_ID,
        tab: "Game_Predictions",
        url: sheetUrl(CALC_ID, "Game_Predictions"),
      },
    ],
  },
];

export function getStep(id: number): StepDef | undefined {
  return STEPS.find((s) => s.id === id);
}
