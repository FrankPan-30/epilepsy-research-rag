# Third-party components

This project's source is licensed under **GNU AGPL v3.0**. Its PDF stack uses the AGPL distribution of PyMuPDF and PyMuPDF4LLM. This project does not provide an Artifex commercial license. See [PyMuPDF licensing](https://pymupdf.io/licensing).

Main components checked for the initial public release:

| Component | Version / revision | Upstream license |
|---|---|---|
| PyMuPDF | 1.26.7 | AGPL-3.0 or separate Artifex commercial license |
| PyMuPDF4LLM | 0.0.27 | AGPL-3.0 or separate Artifex commercial license |
| Sentence Transformers | 5.7.0 | Apache-2.0 |
| MCP Python SDK | 1.30.0 | MIT |
| RapidOCR ONNX Runtime | 1.4.4 | Apache-2.0 |
| multilingual-e5-small | `614241f622f53c4eeff9890bdc4f31cfecc418b3` | MIT, per upstream model card |

The model is downloaded separately from [intfloat/multilingual-e5-small](https://huggingface.co/intfloat/multilingual-e5-small). Model weights and third-party package binaries are not included in this repository. Transitive dependencies retain their own licenses; consult their distributions and the pinned dependency list.

The project license covers project source and original synthetic examples. It does not grant redistribution rights to papers, Zotero library contents, patient data or other material supplied by users.
