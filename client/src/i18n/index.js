import { createI18n } from "vue-i18n";
import en from "./locales/en.json";
import zhTW from "./locales/zh-TW.json";

export const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "zh-TW", label: "繁體中文" }
];

const STORAGE_KEY = "locale";

function initialLocale() {
  let saved = null;
  try {
    saved = localStorage.getItem(STORAGE_KEY);
  } catch (e) {
    saved = null;
  }
  if (LANGUAGES.some(l => l.code === saved)) return saved;
  // first visit: follow the browser (any Chinese variant -> Traditional Chinese)
  let browser = (navigator.language || "en").toLowerCase();
  return browser.startsWith("zh") ? "zh-TW" : "en";
}

const i18n = createI18n({
  legacy: false,
  globalInjection: true, // $t / $te in templates and this.$t in options API
  locale: initialLocale(),
  fallbackLocale: "en",
  messages: { en, "zh-TW": zhTW },
  missingWarn: false,
  fallbackWarn: false
});

export function setLocale(code) {
  i18n.global.locale.value = code;
  document.documentElement.lang = code;
  try {
    localStorage.setItem(STORAGE_KEY, code);
  } catch (e) {
    /* private mode: keep for this session only */
  }
}

/**
 * The server describes durations in English ("5 minutes", "1 hour"; empty
 * for less than a second). Re-render them in the current language.
 */
export function formatAgo(ago) {
  let match = /(\d+)\s+(year|month|day|hour|minute|second)s?/.exec(ago || "");
  let n = match ? parseInt(match[1], 10) : 0;
  let unit = match ? match[2] : "second";
  return i18n.global.t(`time.${unit}`, { n }, n);
}

/** "Rotated BBox" -> "rotatedBBox" */
export function camelKey(text) {
  let words = String(text).match(/[A-Za-z0-9]+/g) || [];
  return words
    .map((w, i) => (i === 0 ? w.charAt(0).toLowerCase() + w.slice(1) : w.charAt(0).toUpperCase() + w.slice(1)))
    .join("");
}

/**
 * Display-time translation of an English label that is also used as an
 * identifier (tool names, process names, shortcut names, option labels).
 * Falls back to the English text when no translation exists.
 */
export function tr(namespace, text) {
  if (text == null || text === "") return text;
  let key = `${namespace}.${camelKey(text)}`;
  return i18n.global.te(key) ? i18n.global.t(key) : text;
}

// Messages built from English templates with a dynamic part, produced by
// this client (process names) or by the server (task names).
const PATTERNS = {
  process: [
    [/^Copying annotations from (.+)$/, m => ["process.copyingFrom", { from: m[1] }]],
    [/^Generating COCO for (.+)$/, m => ["process.generatingCoco", { name: m[1] }]],
    [/^Loading undo for (.+) instance type$/, m => ["process.loadingUndo", { type: tr("undoType", m[1]) }]]
  ],
  task: [
    [/^Scanning (.+) for new images$/, m => ["taskName.scan", { name: m[1] }]],
    [/^Exporting (.+) into (.+) format$/, m => ["taskName.export", { name: m[1], format: m[2] }]],
    [/^Import COCO format into (.+)$/, m => ["taskName.import", { name: m[1] }]],
    [/^Pre-annotating (.+) with (.+)$/, m => ["taskName.preannotate", { name: m[1], model: m[2] }]],
    [/^Importing video (.+) into (.+)$/, m => ["taskName.video", { file: m[1], name: m[2] }]]
  ]
};

function fromPatterns(kind, namespace, text) {
  for (let [regex, build] of PATTERNS[kind]) {
    let match = regex.exec(text || "");
    if (match) {
      let [key, params] = build(match);
      return i18n.global.t(key, params);
    }
  }
  return tr(namespace, text);
}

export const processLabel = text => fromPatterns("process", "process", text);
export const taskName = text => fromPatterns("task", "taskName", text);

/** Translate outside components (stores, plain modules) */
export function t(key, params) {
  return i18n.global.t(key, params);
}

document.documentElement.lang = i18n.global.locale.value;

export default i18n;
