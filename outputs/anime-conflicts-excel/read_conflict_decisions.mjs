import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const workDir = path.dirname(fileURLToPath(import.meta.url));
const workbookPath = path.join(workDir, "Revision_conflictos_anime_Altoidss.xlsx");
const outputPath = path.join(workDir, "conflict-decisions.json");

const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(workbookPath));
const sheet = workbook.worksheets.getItem("Revisión de conflictos");
const rows = sheet.getRange("A7:Q71").values;

const decisions = rows.map((row) => ({
  decision: String(row[0] ?? "").trim().toUpperCase(),
  classification: String(row[1] ?? "").trim(),
  id: String(row[2] ?? "").trim(),
  localTitle: String(row[3] ?? "").trim(),
  candidateTitle: String(row[9] ?? "").trim(),
  sourceUrl: String(row[16] ?? "").trim(),
}));

await fs.writeFile(outputPath, JSON.stringify(decisions, null, 2) + "\n", "utf8");

const counts = decisions.reduce((result, item) => {
  result[item.decision || "SIN_DECISION"] = (result[item.decision || "SIN_DECISION"] || 0) + 1;
  return result;
}, {});

console.log(JSON.stringify({ outputPath, counts }, null, 2));
