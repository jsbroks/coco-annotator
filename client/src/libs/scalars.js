// Curves of a training, as TensorBoard draws them

/** TensorBoard's smoothing: an exponential moving average, debiased so the
 *  start is not pulled to 0. points: [[x, y], ...] in order; weight 0..1 */
export function smooth(points, weight) {
  if (!weight) return points;
  let last = 0;
  let n = 0;
  return points.map(([x, y]) => {
    if (!Number.isFinite(y)) return [x, y];
    last = last * weight + (1 - weight) * y;
    n++;
    return [x, last / (1 - Math.pow(weight, n))];
  });
}

/** About ``count`` round tick values between lo and hi */
export function niceTicks(lo, hi, count = 5) {
  if (!(hi > lo)) {
    const pad = Math.abs(lo) * 0.1 || 1;
    lo -= pad;
    hi += pad;
  }
  const raw = (hi - lo) / count;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = [1, 2, 2.5, 5, 10].map(m => m * mag).find(s => s >= raw) || 10 * mag;
  const out = [];
  for (let k = Math.ceil(lo / step - 1e-9); k * step <= hi + step * 1e-9; k++) out.push(parseFloat((k * step).toPrecision(12)));
  return { ticks: out, step, lo: Math.min(lo, out[0] ?? lo), hi: Math.max(hi, out[out.length - 1] ?? hi) };
}

/** Short number for an axis or a tooltip */
export function fmtNumber(v) {
  if (v == null || !Number.isFinite(v)) return "–";
  const a = Math.abs(v);
  if (a === 0) return "0";
  if (a >= 1000) return v.toFixed(0);
  if (a >= 10) return v.toFixed(1);
  if (a >= 0.01) return v.toFixed(3);
  return v.toExponential(1);
}

/** A tick label: as many decimals as the step needs (0.25 -> "0.25", 2 -> "2") */
export function fmtTick(v, step) {
  if (!Number.isFinite(v)) return "";
  if (v === 0) return "0";
  const a = Math.abs(v);
  if (a >= 1e5 || (a < 1e-3 && step < 1e-3)) return v.toExponential(1);
  const exp = Math.floor(Math.log10(step) + 1e-9);
  // 0.25 needs one more decimal than 0.2
  const extra = Math.abs(step / Math.pow(10, exp) - 2.5) < 1e-9 ? 1 : 0;
  const decimals = Math.max(0, Math.min(6, -exp + extra));
  return v.toFixed(decimals);
}
