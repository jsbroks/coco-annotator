/**
 * Average colour around a point, from a small copy of the image.
 *
 * Polygon / box tools pick a stroke colour that stands out from the image
 * under the cursor on every mouse move. paper's Raster.getAverageColor draws
 * the full-size image each time (tens of ms on a 12 MP photo), so sample a
 * copy at most ``max`` pixels wide instead (made once per image).
 */
export function makeColorSampler(image, width, height, max = 512) {
  const scale = Math.min(1, max / Math.max(width, height));
  const w = Math.max(1, Math.round(width * scale));
  const h = Math.max(1, Math.round(height * scale));
  const ctx = document.createElement("canvas").getContext("2d", { willReadFrequently: true });
  ctx.canvas.width = w;
  ctx.canvas.height = h;
  ctx.drawImage(image, 0, 0, w, h);
  const data = ctx.getImageData(0, 0, w, h).data;
  const hex = v => Math.round(v).toString(16).padStart(2, "0");

  return {
    /** "#rrggbb" around ``point`` (paper coordinates, image centred on 0,0), or null outside */
    average(point, radius) {
      const cx = (point.x + width / 2) * scale;
      const cy = (point.y + height / 2) * scale;
      const r = Math.max(1, radius * scale);
      const x0 = Math.max(0, Math.floor(cx - r)), x1 = Math.min(w - 1, Math.ceil(cx + r));
      const y0 = Math.max(0, Math.floor(cy - r)), y1 = Math.min(h - 1, Math.ceil(cy + r));
      let sr = 0, sg = 0, sb = 0, n = 0;
      for (let y = y0; y <= y1; y++) {
        for (let x = x0; x <= x1; x++) {
          if ((x - cx) ** 2 + (y - cy) ** 2 > r * r) continue;
          const i = (y * w + x) * 4;
          sr += data[i]; sg += data[i + 1]; sb += data[i + 2]; n++;
        }
      }
      if (!n) return null;
      return "#" + hex(sr / n) + hex(sg / n) + hex(sb / n);
    }
  };
}
