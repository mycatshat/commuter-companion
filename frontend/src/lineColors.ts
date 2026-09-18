// Mirrors backend/app/line_mapping.py's CANONICAL_LINES colours. Duplicated
// client-side rather than fetched from /api/lines -- it's a fixed,
// near-never-changing lookup table, not worth a network round trip before
// the map can draw its first line.
export const LINE_COLORS: Record<string, string> = {
  NSL: "#D42E12",
  EWL: "#009645",
  CGL: "#009645",
  NEL: "#9900AA",
  CCL: "#FA9E0D",
  CEL: "#FA9E0D",
  DTL: "#005EC4",
  TEL: "#9D5B25",
  BPL: "#748477",
  SLRT: "#748477",
  PLRT: "#748477",
};

export function lineColor(line: string): string {
  return LINE_COLORS[line] ?? "#666666";
}
