import axios from "axios";

const base = "/api/help/";

export default {
  helpers(imageId) {
    return axios.get(`${base}helpers/${imageId}`);
  },
  ask(data) {
    return axios.post(base, data);
  },
  inbox() {
    return axios.get(base + "inbox");
  },
  forImage(imageId) {
    return axios.get(`${base}image/${imageId}`);
  },
  reply(id, message, resolve = false) {
    return axios.post(`${base}${id}/reply`, { message, resolve });
  },
  seen(id) {
    return axios.post(`${base}${id}/seen`);
  },
  cancel(id) {
    return axios.post(`${base}${id}/cancel`);
  }
};

/** "3 分鐘前" style, from an ISO date */
export function ago(iso, t) {
  if (!iso) return "";
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return t("help.justNow");
  if (s < 3600) return t("help.minutesAgo", { n: Math.floor(s / 60) });
  if (s < 86400) return t("help.hoursAgo", { n: Math.floor(s / 3600) });
  return t("help.daysAgo", { n: Math.floor(s / 86400) });
}
