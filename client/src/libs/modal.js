// Bootstrap 5 modal helpers (replace the jQuery `$(el).modal(...)` API).
import { Modal } from "bootstrap";

function element(target) {
  return typeof target === "string" ? document.querySelector(target) : target;
}

export function showModal(target) {
  let el = element(target);
  if (el) Modal.getOrCreateInstance(el).show();
}

export function hideModal(target) {
  let el = element(target);
  if (el) Modal.getOrCreateInstance(el).hide();
}

export function onModalHidden(target, handler) {
  let el = element(target);
  if (el) el.addEventListener("hidden.bs.modal", handler);
}

/** a dialog is open: the annotator's keyboard shortcuts wait */
export function modalOpen() {
  return !!document.querySelector(".modal.show");
}

/**
 * A component removed while its dialog was open (e.g. the annotation was
 * cleared) leaves Bootstrap's dark backdrop and a locked page: close the
 * dialogs inside ``root`` properly, and clear a leftover backdrop.
 */
export function closeModalsIn(root) {
  if (root && root.querySelectorAll) {
    root.querySelectorAll(".modal.show").forEach(el => {
      const instance = Modal.getInstance(el);
      if (instance) instance.dispose();
      el.classList.remove("show");
    });
  }
  setTimeout(() => {
    if (document.querySelector(".modal.show")) return;
    document.querySelectorAll(".modal-backdrop").forEach(b => b.remove());
    document.body.classList.remove("modal-open");
    document.body.style.removeProperty("overflow");
    document.body.style.removeProperty("padding-right");
  }, 0);
}
