/**
 * Small stand-in for toastr (same calls, same look via toastr's stylesheet)
 * without jQuery:
 *
 *   toast.success(message, title?, options?)   also error / info / warning
 *
 * Options (toastr names): timeOut, extendedTimeOut, closeButton, tapToDismiss,
 * positionClass, onclick, progressBar. Text is always shown as plain text.
 */
const DEFAULTS = {
  timeOut: 5000,
  extendedTimeOut: 1000,
  closeButton: false,
  tapToDismiss: true,
  positionClass: "toast-top-right",
  onclick: null,
  progressBar: false
};

export const options = {};

const containers = {};

function container(position) {
  let el = containers[position];
  if (el && document.body.contains(el)) return el;
  el = document.createElement("div");
  // toastr's stylesheet styles "#toast-container"; one per position
  el.id = "toast-container";
  el.className = position;
  el.setAttribute("aria-live", "polite");
  el.setAttribute("role", "alert");
  document.body.appendChild(el);
  containers[position] = el;
  return el;
}

function show(type, message, title, opts) {
  const o = { ...DEFAULTS, ...options, ...(opts || {}) };
  const box = container(o.positionClass);
  const el = document.createElement("div");
  el.className = `toast toast-${type}`;
  // Bootstrap hides ".toast" without ".show"; toastr's fade-in set this too
  el.style.display = "block";

  if (o.closeButton) {
    const close = document.createElement("button");
    close.type = "button";
    close.className = "toast-close-button";
    close.setAttribute("aria-label", "Close");
    close.textContent = "×";
    close.addEventListener("click", e => {
      e.stopPropagation();
      hide(true);
    });
    el.appendChild(close);
  }
  let bar = null;
  if (o.progressBar && o.timeOut > 0) {
    bar = document.createElement("div");
    bar.className = "toast-progress";
    el.appendChild(bar);
  }
  if (title) {
    const t = document.createElement("div");
    t.className = "toast-title";
    t.textContent = String(title);
    el.appendChild(t);
  }
  if (message != null && message !== "") {
    const m = document.createElement("div");
    m.className = "toast-message";
    m.textContent = String(message);
    el.appendChild(m);
  }

  let timer = null;
  let frame = null;
  let endsAt = 0;
  let span = 0;
  let gone = false;

  function hide(now = false) {
    if (gone) return;
    gone = true;
    clearTimeout(timer);
    cancelAnimationFrame(frame);
    el.style.transition = "opacity 0.3s";
    el.style.opacity = "0";
    setTimeout(() => {
      el.remove();
      if (!box.children.length) {
        box.remove();
        // only if it is still this box (clear() may have made a new one)
        if (containers[o.positionClass] === box) delete containers[o.positionClass];
      }
    }, now ? 150 : 300);
  }
  function tick() {
    if (!bar || gone) return;
    bar.style.width = `${Math.max(0, ((endsAt - Date.now()) / span) * 100)}%`;
    frame = requestAnimationFrame(tick);
  }
  function wait(ms) {
    if (!(ms > 0)) return;
    clearTimeout(timer);
    span = ms;
    endsAt = Date.now() + ms;
    timer = setTimeout(() => hide(), ms);
    cancelAnimationFrame(frame);
    tick();
  }

  el.addEventListener("mouseenter", () => {
    clearTimeout(timer);
    cancelAnimationFrame(frame);
    if (bar) bar.style.width = "0%";
  });
  el.addEventListener("mouseleave", () => {
    if (o.timeOut > 0 || o.extendedTimeOut > 0) wait(o.extendedTimeOut);
  });
  el.addEventListener("click", e => {
    if (typeof o.onclick === "function") o.onclick(e);
    if (o.tapToDismiss) hide();
  });

  // newest on top, like toastr
  box.insertBefore(el, box.firstChild);
  el.style.opacity = "0";
  requestAnimationFrame(() => {
    el.style.transition = "opacity 0.3s";
    el.style.opacity = "";
  });
  wait(o.timeOut);
  return el;
}

function clear() {
  Object.values(containers).forEach(el => el.remove());
  Object.keys(containers).forEach(k => delete containers[k]);
}

const toast = {
  options,
  success: (message, title, opts) => show("success", message, title, opts),
  error: (message, title, opts) => show("error", message, title, opts),
  info: (message, title, opts) => show("info", message, title, opts),
  warning: (message, title, opts) => show("warning", message, title, opts),
  clear
};

export default toast;
