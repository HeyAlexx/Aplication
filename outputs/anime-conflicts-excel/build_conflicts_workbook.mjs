import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const workDir = path.dirname(fileURLToPath(import.meta.url));
const sourcePath = path.resolve(workDir, "..", "anime-conflicts-review.json");
const outputPath = path.join(workDir, "Revision_conflictos_anime_Altoidss.xlsx");
const previewPath = path.join(workDir, "preview.png");

const source = JSON.parse(await fs.readFile(sourcePath, "utf8"));
const workbook = Workbook.create();
const sheet = workbook.worksheets.add("Revisión de conflictos");
sheet.showGridLines = false;

const colors = {
  obsidian: "#04151A",
  darkTeal: "#092828",
  gunmetal: "#163E3C",
  teal: "#325F57",
  blueGray: "#6F9487",
  pale: "#DCE9E4",
  white: "#FFFFFF",
  green: "#C6EFCE",
  greenText: "#006100",
  yellow: "#FFF2CC",
  yellowText: "#7F6000",
  red: "#F4CCCC",
  redText: "#9C0006",
  purple: "#E4D7F5",
  purpleText: "#4C247A",
};

sheet.getRange("A1:Q1").merge();
sheet.getRange("A1").values = [["ALTOIDSS | Revisión de conflictos de anime"]];
sheet.getRange("A1:Q1").format = {
  fill: colors.obsidian,
  font: { bold: true, color: colors.white, size: 18 },
  verticalAlignment: "center",
};
sheet.getRange("A1:Q1").format.rowHeight = 34;

sheet.getRange("A2:Q2").merge();
sheet.getRange("A2").values = [[
  "Selecciona OK únicamente cuando aceptes sustituir o completar los datos locales con el candidato de la API. RECHAZAR conserva el registro local.",
]];
sheet.getRange("A2:Q2").format = {
  fill: colors.darkTeal,
  font: { color: colors.pale, italic: true },
  wrapText: true,
  verticalAlignment: "center",
};
sheet.getRange("A2:Q2").format.rowHeight = 32;

sheet.getRange("A3:H3").values = [[
  "Total pendientes",
  "Conflicto probable",
  "Alias o título distinto",
  "Revisión recomendada",
  "Estreno futuro",
  "Aprobados",
  "Rechazados",
  "Sin decisión",
]];
sheet.getRange("A4:E4").formulas = [[
  "=COUNTA(C7:C71)",
  '=COUNTIF(B7:B71,"Conflicto probable")',
  '=COUNTIF(B7:B71,"Alias o título distinto")',
  '=COUNTIF(B7:B71,"Revisión recomendada")',
  '=COUNTIF(B7:B71,"Estreno futuro o sin publicar")',
]];
sheet.getRange("F4:H4").formulas = [[
  '=COUNTIF(A7:A71,"OK")',
  '=COUNTIF(A7:A71,"RECHAZAR")',
  '=COUNTBLANK(A7:A71)',
]];
sheet.getRange("A3:H3").format = {
  fill: colors.teal,
  font: { bold: true, color: colors.white },
  horizontalAlignment: "center",
  wrapText: true,
};
sheet.getRange("A4:H4").format = {
  fill: colors.pale,
  font: { bold: true, color: colors.obsidian, size: 14 },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  borders: { preset: "outside", style: "thin", color: colors.blueGray },
};
sheet.getRange("A3:H4").format.rowHeight = 26;

const headers = [
  "Decisión",
  "Clasificación",
  "ID local",
  "Anime local",
  "Año local",
  "Estación local",
  "Formato local",
  "Temporada local",
  "Capítulos",
  "Candidato API",
  "Año API",
  "Estación API",
  "Formato API",
  "Fuente",
  "Puntaje",
  "Conflictos detectados",
  "URL fuente",
];

const rows = source.map((item) => {
  const candidate = item.candidate ?? {};
  return [
    "",
    item.classification ?? "",
    item.id ?? "",
    item.local?.title ?? "",
    item.local?.emissionYear ?? null,
    item.local?.emissionSeason ?? "",
    item.local?.format ?? "",
    item.local?.activeSeason ?? "",
    item.local?.chapters ?? null,
    candidate.title ?? "Sin candidato",
    candidate.emissionYear ?? null,
    candidate.emissionSeason ?? "",
    candidate.format ?? "",
    candidate.source ?? "",
    item.score ?? null,
    Array.isArray(item.conflicts) ? item.conflicts.join(" ") : "",
    candidate.sourceUrl ?? "",
  ];
});

sheet.getRange("A6:Q6").values = [headers];
sheet.getRange(`A7:Q${6 + rows.length}`).values = rows;
sheet.getRange("A6:Q6").format = {
  fill: colors.gunmetal,
  font: { bold: true, color: colors.white },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
  borders: { preset: "outside", style: "medium", color: colors.teal },
};

const lastRow = 6 + rows.length;
const dataRange = sheet.getRange(`A7:Q${lastRow}`);
dataRange.format = {
  font: { color: colors.obsidian, size: 10 },
  verticalAlignment: "top",
  borders: {
    insideHorizontal: { style: "thin", color: "#D7E1DD" },
    bottom: { style: "thin", color: "#D7E1DD" },
  },
};
sheet.getRange(`D7:D${lastRow}`).format.wrapText = true;
sheet.getRange(`J7:J${lastRow}`).format.wrapText = true;
sheet.getRange(`P7:P${lastRow}`).format.wrapText = true;
sheet.getRange(`Q7:Q${lastRow}`).format.wrapText = true;
sheet.getRange(`E7:E${lastRow}`).format.numberFormat = "0";
sheet.getRange(`I7:I${lastRow}`).format.numberFormat = "0";
sheet.getRange(`K7:K${lastRow}`).format.numberFormat = "0";
sheet.getRange(`O7:O${lastRow}`).format.numberFormat = "0.00";

sheet.getRange(`A7:A${lastRow}`).dataValidation = {
  rule: { type: "list", values: ["OK", "RECHAZAR"] },
};
sheet.getRange(`A7:A${lastRow}`).conditionalFormats.add("containsText", {
  text: "OK",
  format: { fill: colors.green, font: { bold: true, color: colors.greenText } },
});
sheet.getRange(`A7:A${lastRow}`).conditionalFormats.add("containsText", {
  text: "RECHAZAR",
  format: { fill: colors.red, font: { bold: true, color: colors.redText } },
});
sheet.getRange(`B7:B${lastRow}`).conditionalFormats.add("containsText", {
  text: "Conflicto probable",
  format: { fill: colors.green, font: { color: colors.greenText } },
});
sheet.getRange(`B7:B${lastRow}`).conditionalFormats.add("containsText", {
  text: "Revisión recomendada",
  format: { fill: colors.yellow, font: { color: colors.yellowText } },
});
sheet.getRange(`B7:B${lastRow}`).conditionalFormats.add("containsText", {
  text: "Alias o título distinto",
  format: { fill: colors.purple, font: { color: colors.purpleText } },
});
sheet.getRange(`B7:B${lastRow}`).conditionalFormats.add("containsText", {
  text: "Estreno futuro o sin publicar",
  format: { fill: colors.red, font: { color: colors.redText } },
});

const table = sheet.tables.add(`A6:Q${lastRow}`, true, "AnimeConflictReview");
table.style = "TableStyleMedium2";
table.showFilterButton = true;
table.showBandedRows = true;

sheet.freezePanes.freezeRows(6);
sheet.freezePanes.freezeColumns(4);

const widths = {
  A: 14, B: 24, C: 22, D: 34, E: 11, F: 14, G: 14, H: 15, I: 11,
  J: 42, K: 11, L: 14, M: 13, N: 12, O: 10, P: 62, Q: 42,
};
for (const [column, width] of Object.entries(widths)) {
  sheet.getRange(`${column}:${column}`).format.columnWidth = width;
}
sheet.getRange(`A7:Q${lastRow}`).format.rowHeight = 48;
sheet.getRange("A6:Q6").format.rowHeight = 32;

const inspection = await workbook.inspect({
  kind: "table",
  range: "Revisión de conflictos!A1:Q12",
  include: "values,formulas",
  tableMaxRows: 12,
  tableMaxCols: 17,
  maxChars: 7000,
});
console.log(inspection.ndjson);

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "final formula error scan",
});
console.log(errors.ndjson);

const preview = await workbook.render({
  sheetName: "Revisión de conflictos",
  range: "A1:Q15",
  scale: 1,
  format: "png",
});
await fs.writeFile(previewPath, new Uint8Array(await preview.arrayBuffer()));

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(JSON.stringify({ outputPath, previewPath, rows: rows.length }));
