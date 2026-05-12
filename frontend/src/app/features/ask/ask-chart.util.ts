function isNumeric(v: unknown): boolean {
  return typeof v === 'number' || (typeof v === 'string' && v !== '' && !Number.isNaN(Number(v)));
}

function toNumber(v: unknown): number {
  return typeof v === 'number' ? v : Number(v);
}

export interface BarChartModel {
  kind: 'bar';
  results: { name: string; value: number }[];
}

export interface ScatterChartModel {
  kind: 'scatter';
  results: { name: string; series: { name: string; x: number; y: number }[] }[];
}

export interface LineChartModel {
  kind: 'line';
  results: { name: string; series: { name: string; value: number }[] }[];
}

export type ChartModel = BarChartModel | ScatterChartModel | LineChartModel | { kind: 'none' };

export function buildChartModel(rows: Record<string, unknown>[]): ChartModel {
  if (!rows.length) {
    return { kind: 'none' };
  }
  const keys = Object.keys(rows[0]);
  if (keys.length < 2) {
    return { kind: 'none' };
  }

  const numericCols = keys.filter((k) => rows.every((r) => isNumeric(r[k])));
  const stringCols = keys.filter((k) => !numericCols.includes(k));

  if (numericCols.length >= 2 && stringCols.length === 0) {
    const [x, y] = numericCols;
    const series = rows.map((r, i) => ({
      name: `p${i}`,
      x: toNumber(r[x]),
      y: toNumber(r[y]),
    }));
    return {
      kind: 'scatter',
      results: [{ name: `${x} vs ${y}`, series }],
    };
  }

  if (stringCols.length >= 1 && numericCols.length >= 1) {
    const cat = stringCols[0];
    const val = numericCols[0];
    const results = rows.map((r) => ({
      name: String(r[cat]),
      value: toNumber(r[val]),
    }));
    return { kind: 'bar', results };
  }

  const timeLike = keys.find((k) =>
    rows.some((r) => typeof r[k] === 'string' && /\d{4}-\d{2}/.test(String(r[k]))),
  );
  if (timeLike && numericCols.length >= 1) {
    const val = numericCols[0];
    const results = [
      {
        name: val,
        series: rows.map((r) => ({
          name: String(r[timeLike]),
          value: toNumber(r[val]),
        })),
      },
    ];
    return { kind: 'line', results };
  }

  return { kind: 'none' };
}
