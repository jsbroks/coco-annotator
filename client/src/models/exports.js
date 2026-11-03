import axios from "axios";

const baseURL = "/api/export";

export default {
  /** the address the browser can download from itself (very large files) */
  downloadUrl(id) {
    return `${baseURL}/${id}/download`;
  },
  /**
   * Download into the page, then save: ``onProgress({loaded, total})`` while
   * it comes in; ``signal`` (AbortController) cancels it.
   */
  download(id, dataset, { onProgress = null, signal = null } = {}) {
    return axios({
      url: `${baseURL}/${id}/download`,
      method: "GET",
      responseType: "blob",
      signal,
      onDownloadProgress: onProgress ? e => onProgress({ loaded: e.loaded, total: e.total || 0 }) : undefined
    }).then(response => {
      // the server names the file (.json for COCO, .zip for YOLO)
      const disposition = response.headers["content-disposition"] || "";
      const utf8 = /filename\*=UTF-8''([^;]+)/i.exec(disposition);
      const plain = /filename="?([^";]+)"?/i.exec(disposition);
      const name = utf8 ? decodeURIComponent(utf8[1]) : plain ? plain[1] : `${dataset}-${id}.json`;
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", name);
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => window.URL.revokeObjectURL(url), 1000);
    });
  }
};
