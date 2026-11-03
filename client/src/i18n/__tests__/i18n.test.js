import { describe, it, expect } from "vitest";
import en from "../locales/en.json";
import zhTW from "../locales/zh-TW.json";
import i18n, { setLocale, tr, formatAgo } from "../index";

function keys(obj, prefix = "") {
  return Object.entries(obj).flatMap(([k, v]) =>
    typeof v === "object" ? keys(v, `${prefix}${k}.`) : [`${prefix}${k}`]
  );
}

describe("locales", () => {
  it("every English message has a Traditional Chinese translation", () => {
    const zh = new Set(keys(zhTW));
    expect(keys(en).filter(k => !zh.has(k))).toEqual([]);
  });

  it("switches language and translates identifiers at display time", () => {
    setLocale("zh-TW");
    expect(i18n.global.t("navBar.datasets")).toBe("資料集");
    expect(tr("toolbar", "Rotated BBox")).toBe("旋轉框");
    expect(tr("toolbar", "Unknown Tool")).toBe("Unknown Tool");
    expect(formatAgo("5 minutes")).toBe("5 分鐘");
    expect(i18n.global.t("imageCard.annotations", { n: 3 }, 3)).toBe("3 個標註");

    setLocale("en");
    expect(tr("toolbar", "Rotated BBox")).toBe("Rotated BBox");
    expect(formatAgo("1 hour")).toBe("1 hour");
    expect(formatAgo("")).toBe("0 seconds");
    expect(i18n.global.t("imageCard.annotations", { n: 1 }, 1)).toBe("1 annotation");
  });
});
