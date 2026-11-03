// Where the in-app help links point (this fork, not the original project).
export const REPO_URL = "https://github.com/Tsaicc-biovlsi/coco-annotator";
export const DOCS_URL = `${REPO_URL}#readme`;
export const ISSUES_URL = `${REPO_URL}/issues`;
// GitHub anchors of README.md sections
export const docsSection = anchor => `${REPO_URL}#${encodeURIComponent(anchor)}`;
