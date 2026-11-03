import { reactive } from "vue";
import axios from "axios";

/**
 * The signed-in reviewer's saved reasons for rejecting, shared by the
 * annotator and quick review. ``list`` is null until loaded, or when the
 * user never saved any (then the built-in suggestions are shown).
 */
export const rejectReasons = reactive({ list: null, loaded: false, user: null });

let loading = null;

export function loadRejectReasons(user = null) {
  // signed in as someone else in the same tab: their own list
  if (rejectReasons.user !== user) {
    rejectReasons.list = null;
    rejectReasons.loaded = false;
    rejectReasons.user = user;
    loading = null;
  }
  if (rejectReasons.loaded) return Promise.resolve();
  if (!loading) {
    loading = axios
      .get("/api/user/reject-reasons")
      .then(r => {
        if (rejectReasons.user !== user) return; // switched user meanwhile
        rejectReasons.list = r.data.reasons;
        rejectReasons.loaded = true;
      })
      .catch(() => {})
      .finally(() => {
        if (rejectReasons.user === user) loading = null;
      });
  }
  return loading;
}

export async function saveRejectReasons(list) {
  const r = await axios.put("/api/user/reject-reasons", { reasons: list });
  rejectReasons.list = r.data.reasons;
  rejectReasons.loaded = true;
  return rejectReasons.list;
}

/** the reasons to show: the saved ones, or the suggestions */
export function reasonsOr(defaults) {
  return rejectReasons.list === null ? defaults : rejectReasons.list;
}

/** add a picked reason to what is typed already */
export function withReason(note, reason) {
  const text = (note || "").trim();
  if (!text) return reason;
  if (text.split(/[；;\n]/).map(s => s.trim()).includes(reason)) return text;
  return `${text}；${reason}`;
}
