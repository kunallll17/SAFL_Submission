# External code, models and datasets

Versions and licence identifiers below were read from installed package metadata in the project's environment. The exact dependency closure is pinned in `requirements.txt`. Upstream licence texts remain in each installed distribution's metadata; no dependencies are vendored in the source archive.

| Package | Version tested | Licence identifier | Role |
|---|---|---|---|
| FastAPI | 0.162.0 | MIT | Local owner and mock-gateway HTTP APIs |
| Uvicorn | 0.54.0 | BSD-3-Clause | ASGI server |
| cryptography | 50.0.2 | Apache-2.0 OR BSD-3-Clause | Ed25519 implementation |
| Pydantic | 2.14.2 | MIT | Strict schema validation |
| HTTPX | 0.28.1 | BSD-3-Clause | Loopback gateway and proposal adapter requests |
| pytest | 9.2.0 | MIT | Regression tests |
| Starlette | 1.10.0 | BSD-3-Clause | Transitive ASGI and test infrastructure |
| cffi | 2.1.1 | MIT-0 | Transitive cryptography dependency |

The complete package/licence inventory is generated in `evidence/dependencies.json`, including transitive dependencies. Python and SQLite are platform components. Frontend code uses browser APIs and system fonts; there are no external JavaScript packages, remote font requests, analytics, CDNs or third-party image assets.

The report is produced with ReportLab 4.4.9 (BSD licence), and checked with pypdf 6.10.0 (BSD-3-Clause) and Poppler. These are document-build tools, not required to run the application. The report uses standard PDF base fonts (Helvetica and Courier). No font files are distributed in the source archive.

The core app needs no model. The optional untrusted proposal agent uses [Qwen/Qwen2.5-1.5B-Instruct-GGUF](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF), Apache-2.0, revision `91cad51170dc346986eccefdc2dd33a9da36ead9`, quantization Q4_K_M. It runs through [llama.cpp](https://github.com/ggml-org/llama.cpp), MIT, build b12020, Windows x64 CPU. `evidence/local_model_runtime.json` records exact source URLs, byte lengths and verified SHA-256 checksums. The optional installer downloads roughly 1.14 GB; binaries and weights remain in ignored `.local-model/` and are not distributed in the source archive. The model repository and runtime archive include their upstream licence texts.

No third-party dataset or paid inference service was used. Scenario text, synthetic handles, fixture actions, live-pilot attack inputs and generated mutations were created for this project. MAPS is cited for context; no MAPS data is included and no score on MAPS is claimed. Real local-model output is distinguished from the authored policy fixtures in `evidence/model_pilot.json`.

Development tools: OpenAI Codex (GPT-6) assisted implementation, testing and documentation. The optional runtime proposer is Qwen2.5; no model participates in the trusted authorization path.

Team ownership and publication consents are separate from these third-party licences. This draft does not assign the team's original work to the organizers or publish it.

The guided demo redesign follows **unslop by Damir Sokolovsky** ([@heydamir](https://x.com/heydamir)), [heydamir/unslop](https://github.com/heydamir/unslop), licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Its design process was adapted to simplify this project's task and approval flow. No upstream images, fonts or runtime scripts were copied.

The included `brag.mp4` demo uses credited music, sound effects and rendered fonts. See [video credits and licences](docs/VIDEO_CREDITS.md), including Sascha Ende (CC BY 4.0) and Kenney (CC0).
