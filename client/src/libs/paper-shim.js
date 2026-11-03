// paper.js relies on sloppy-mode semantics (it assigns properties to values
// that may be strings), which throws once the library is bundled as a strict
// ES module. It is therefore loaded as a classic <script> (see vite.config.js
// and index.html) and re-exported here; `import paper from "paper"` resolves
// to this file.
const paper = window.paper;
export default paper;
