# Weekly Product Review Pulse — Edge Cases & Corner Cases

This document catalogs known edge cases, corner cases, and failure scenarios for the **Groww Weekly Review Pulse** v1. Each entry describes the condition, expected system behavior, and implementation notes.

Derived from [architecture.md](./architecture.md) and [implementation-plan.md](./implementation-plan.md).

---

## How to Read This Document

| Field | Meaning |
|---|---|
| **ID** | Stable reference (e.g. `ING-01`) |
| **Severity** | `Critical` — blocks delivery or causes duplicates; `High` — bad output or data loss; `Medium` — degraded but recoverable; `Low` — cosmetic or rare |
| **Expected behavior** | What the system must do |
| **Test hint** | Suggested way to verify handling |

---

## Table of Contents

1. [Configuration & Foundation](#1-configuration--foundation)
2. [Run Identity, Time & CLI](#2-run-identity-time--cli)
3. [Play Store Ingestion](#3-play-store-ingestion)
4. [Preprocessing & PII](#4-preprocessing--pii)
5. [Embeddings & Clustering](#5-embeddings--clustering)
6. [LLM Summarization & Quotes](#6-llm-summarization--quotes)
7. [Report & Email Rendering](#7-report--email-rendering)
8. [Google Docs MCP](#8-google-docs-mcp)
9. [Gmail MCP](#9-gmail-mcp)
10. [MCP Client & Orchestration](#10-mcp-client--orchestration)
11. [Idempotency, Ledger & Recovery](#11-idempotency-ledger--recovery)
12. [Scheduling & Operations](#12-scheduling--operations)
13. [Security, Privacy & Abuse](#13-security-privacy--abuse)
14. [Data, Storage & Concurrency](#14-data-storage--concurrency)

---

## 1. Configuration & Foundation

| ID | Scenario | Severity | Expected behavior | Test hint |
|---|---|---|---|---|
| CFG-01 | `config/groww.yaml` missing or malformed | Critical | Exit code 2; clear config parse error; no pipeline start | Rename file; run CLI |
| CFG-02 | Invalid Groww `package_id` in config | High | Fail at config validation or first ingest with "app not found" | Use fake package ID |
| CFG-03 | Missing `google.doc_id` placeholder / empty doc ID | Critical | Fail before MCP delivery; never append to unknown doc | Empty doc_id in yaml |
| CFG-04 | `config/pulse.yaml` has invalid clustering params (negative, zero) | Medium | Fail at config load with validation message | Set `min_cluster_size: 0` |
| CFG-05 | OAuth secrets or `GROQ_API_KEY` accidentally placed under `pulse/` | Critical | Code review / lint gate rejects; runtime must not read them from agent | Static scan in CI |
| CFG-06 | MCP server auth token file missing | Critical | MCP server fails fast with auth setup instructions; orchestrator marks run FAILED | Delete token file |
| CFG-07 | Staging config points to production doc ID | Critical | Environment validation checklist; separate yaml or env overlay | Manual config audit |
| CFG-08 | Recipient list empty in `groww.yaml` | High | Fail before Gmail send with "no recipients"; Doc delivery may still succeed if `--skip-email` not set | Empty `recipients: []` |
| CFG-09 | Unknown product passed to CLI (`--product other`) | Medium | Exit code 2; only `groww` accepted in v1 | `run --product other` |
| CFG-10 | Config file encoding issues (UTF-8 BOM, non-UTF8) | Low | Loader handles UTF-8; fail with encoding error if unreadable | Save yaml as Latin-1 |
| CFG-11 | `GROQ_API_KEY` missing or invalid in `.env` | Critical | Fail at analyze stage with clear auth error; no partial publish | Unset env var |

---

## 2. Run Identity, Time & CLI

| ID | Scenario | Severity | Expected behavior | Test hint |
|---|---|---|---|---|
| RUN-01 | `--week` omitted on Monday 00:30 IST vs Sunday 23:30 UTC same instant | High | Week resolved consistently in `Asia/Kolkata`; document boundary rule in code | Run at week boundary |
| RUN-02 | Invalid ISO week string (`2026-W99`, `2026-W00`) | Medium | Exit code 2; validation error | Bad `--week` arg |
| RUN-03 | Backfill for future ISO week | Medium | Reject or warn; do not deliver "future" week reports | `--week` next year |
| RUN-04 | Backfill for week before Groww app existed on Play Store | Medium | Ingest returns few/zero reviews → fail `min_reviews_for_run` | Very old week |
| RUN-05 | Two runs same week with different `--email-mode` (draft then send) | High | First completed run blocks second unless `--force`; email idempotency prevents duplicate even on force if message exists | Draft then send same week |
| RUN-06 | `--dry-run` with completed ledger entry | Low | Still runs pipeline locally OR short-circuits after render; never calls MCP; no ledger COMPLETED update | Dry-run completed week |
| RUN-07 | `--force-refresh` with corrupted local cache | Medium | Ignore corrupt cache; re-fetch from Play Store; log cache invalidation | Truncate `reviews.json` |
| RUN-08 | `--from-stage` points to stage without prior artifacts | High | Fail with "missing report_{run_id}.json"; suggest full run or earlier stage | `--from-stage render` with no report |
| RUN-09 | `--from-stage email` but Doc section never created | High | Fail; require docs stage success or manual section_anchor_url | Skip docs, retry email |
| RUN-10 | Leap year / ISO week 53 edge (years with 53 weeks) | Medium | `run_id` format still valid; heading dates computed correctly | Week 2020-W53 |
| RUN-11 | CLI invoked with incompatible flag combo (`--dry-run --email-mode send`) | Low | Dry-run wins; email mode ignored; log warning | Combined flags |
| RUN-12 | Process killed mid-run (SIGINT, OOM) | High | Ledger remains `FAILED` or partial `PENDING`; retry safe via idempotency layers | Kill during DELIVERING_DOCS |

---

## 3. Play Store Ingestion

| ID | Scenario | Severity | Expected behavior | Test hint |
|---|---|---|---|---|
| ING-01 | Play Store scraper rate-limits or returns 429 | High | Exponential backoff; 3 retries; then FAILED | Mock 429 responses |
| ING-02 | Play Store layout/API change breaks scraper | Critical | Parse error logged; FAILED; cached last-good run unaffected | Simulate schema change |
| ING-03 | Network timeout mid-pagination | High | Retry from last successful page or full retry; partial cache not marked complete | Drop connection on page 3 |
| ING-04 | Review count below `min_reviews_for_run` (default 50) | High | FAILED; no LLM, no delivery; clear error message | Small window or new app |
| ING-05 | Exactly at threshold (e.g. 50 reviews) | Low | Proceed normally | Boundary count fixture |
| ING-06 | Duplicate `review_id` across pagination pages | Medium | Dedupe keeps first occurrence; log duplicate count | Inject duplicate IDs |
| ING-07 | Missing or null `review_id` from scraper | Medium | Generate stable hash from text+timestamp+rating; log warning | Null ID in mock data |
| ING-08 | Review text is null/empty but rating exists | Low | Drop in normalize stage; do not count toward min_reviews | Empty text reviews |
| ING-09 | Review timestamp outside 12-week window due to clock skew | Medium | Filter strictly by window bounds after fetch | Edge timestamp reviews |
| ING-10 | Groww app unpublished or region-blocked | Critical | Ingest fails or returns zero; FAILED with actionable message | Invalid/unlisted app |
| ING-11 | Extremely large review volume (10k+ in window) | Medium | Complete ingest; downstream token/cluster limits may apply; log duration | Stress test |
| ING-12 | Cached raw JSON from prior run used without `--force-refresh` | Low | Skip network; use cache; log "cache hit" | Second ingest same run_id |
| ING-13 | Cache exists but for different `review_window_weeks` config | High | Invalidate cache if window config changed; or store window in cache metadata | Change window weeks, re-run |
| ING-14 | Same review edited by user on Play Store between runs | Low | Treated as same `review_id`; latest scrape wins on `--force-refresh` | Refresh mid-week |
| ING-15 | Non-English reviews (Hindi script, Roman Hinglish) | Medium | Drop non-Latin script; keep Roman Hinglish; clustering works on English/Roman corpus | Multilingual fixture |
| ING-16 | Reviews contain only emoji or star-only ratings | Low | Drop ultra-short in normalize; rating-only may remain if text empty | Emoji-only reviews |
| ING-17 | Scraper returns reviews in non-chronological order | Low | Sort by timestamp before window filter | Unsorted mock feed |

---

## 4. Preprocessing & PII

| ID | Scenario | Severity | Expected behavior | Test hint |
|---|---|---|---|---|
| PRE-01 | Email embedded in review text | High | Redact to `[EMAIL]` before LLM and publish | Review with email |
| PRE-02 | Indian phone formats (+91, 10-digit, spaced) | High | Redact to `[PHONE]` | Various phone formats |
| PRE-03 | PAN/Aadhaar-like numeric sequences | High | Redact to `[ID]` | Fake ID patterns |
| PRE-04 | URL in review ( phishing, support link) | Medium | Redact full URL or domain-only per config | URL-heavy review |
| PRE-05 | PII split across lines or with unicode homoglyphs | Medium | Best-effort regex; document known limits; prefer over-redaction | Obfuscated email |
| PRE-06 | Redaction breaks quote substring match later | High | Quote validation uses same normalized/scrubbed text as LLM input | Quote spanning redacted phone |
| PRE-07 | HTML entities (`&amp;`, `&#39;`) in review text | Low | Decode/strip in normalize | Encoded reviews |
| PRE-08 | Excessive whitespace, newlines, tabs | Low | Collapse whitespace | Messy formatting |
| PRE-09 | Review shorter than `min_words` threshold (default 8) | Low | Dropped; excluded from clustering | 7-word review |
| PRE-10 | Non-Latin script in review (Devanagari etc.) | Medium | Dropped when `reject_non_latin_script: true`; Roman Hinglish kept | Hindi-script fixture |
| PRE-11 | All reviews dropped after normalize | High | FAILED — equivalent to too few reviews | Aggressive `min_words` |
| PRE-12 | Duplicate text different IDs (copy-paste reviews) | Low | Both kept for clustering; may cluster together | Duplicate text fixture |
| PRE-13 | User name field contains PII (if captured) | High | Never publish username; strip before any output | Scraper returns username |
| PRE-14 | Surrogate pairs / rare unicode in reviews | Low | UTF-8 safe handling end-to-end | Unicode edge strings |

---

## 5. Embeddings & Clustering

| ID | Scenario | Severity | Expected behavior | Test hint |
|---|---|---|---|---|
| CLU-01 | All reviews assigned HDBSCAN noise (`label = -1`) | High | Rating-band fallback (1–3★ vs 4–5★); if still empty → FAILED | Random/disparate reviews |
| CLU-02 | Single dominant cluster (90%+ reviews) | Medium | Still produce up to K themes; sub-cluster or take secondary clusters | Homogeneous corpus |
| CLU-03 | Many tiny clusters below `min_cluster_size` | Medium | Exclude from top themes; may yield fewer than K themes | Tune min_cluster_size |
| CLU-04 | Fewer valid clusters than `top_k_themes` | Low | Report only available themes (e.g. 2 themes not 5) | Small diverse set |
| CLU-05 | UMAP fails on very small dataset (~50 reviews) | Medium | Reduce UMAP params adaptively or skip UMAP for n&lt;100 | Minimum corpus |
| CLU-06 | Identical review texts (spam templates) | Medium | Cluster together; one theme; quotes deduped | Template spam |
| CLU-07 | Recency × urgency weighting ranks small recent complaint above large old praise cluster | Low | By design; formula: `size × recency × urgency` | Mixed age clusters |
| CLU-08 | Embedding model download fails (offline/air-gapped) | High | FAILED with model load error; document offline model path | No network on first run |
| CLU-09 | Out-of-memory during embedding large corpus | High | Batch encoding (batch size 64); FAILED if unrecoverable | 10k+ reviews |
| CLU-10 | Rating-only reviews with minimal text | Medium | May land in noise; rating fallback groups 1-star vs 5-star | Short negative reviews |
| CLU-11 | Cluster contains contradictory sentiments | Medium | LLM summarizes dominant sentiment; quotes may show nuance | Mixed cluster |
| CLU-12 | Non-deterministic UMAP/HDBSCAN across runs | Medium | Set random seeds where supported; document minor theme drift week-to-week | Two runs same data |
| CLU-13 | Parquet embedding cache corrupted | Medium | Regenerate embeddings; log cache miss | Truncate `embeddings_{run_id}.parquet` |
| CLU-14 | One-star review bombing spike in window | Low | Appears as theme if cluster size sufficient; urgency boost in ranking | Many 1-star similar |
| CLU-15 | Generic 5★ praise forms weak cluster or noise | Medium | Excluded from top themes via low urgency score; expected HDBSCAN noise | "Great app easy to use" spam |
| CLU-16 | `two_band: true` yields fewer than 5 themes in one band | Low | Report available themes only (e.g. 3 pain + 1 praise) | Enable two_band on small corpus |

---

## 6. LLM Summarization & Quotes

| ID | Scenario | Severity | Expected behavior | Test hint |
|---|---|---|---|---|
| LLM-01 | Prompt injection in review ("Ignore previous instructions…") | Critical | System prompt treats reviews as data; output unchanged; no tool/exec behavior | Injection fixture |
| LLM-02 | LLM hallucinates quote not in source text | High | Quote validation fails; quote dropped | Mock bad LLM response |
| LLM-03 | LLM paraphrases instead of verbatim quote | High | Validation fails; one re-prompt with stricter instructions | Paraphrased quote |
| LLM-04 | All quotes fail validation for a cluster | High | Re-invoke LLM once; if still empty, drop theme or fail if no themes left | Adversarial LLM |
| LLM-05 | LLM returns zero themes / empty response | High | FAILED if no valid themes remain | Empty JSON response |
| LLM-06 | Token budget exceeded mid-run (`max_tokens_per_run`, default 8000) | High | Abort with FAILED; log tokens used; no partial publish | Low token cap |
| LLM-07 | Per-cluster budget exceeded (`max_tokens_per_cluster`, default 1200) | Medium | Truncate cluster excerpts (20 reviews × 500 chars max); or skip cluster | Huge cluster |
| LLM-08 | Groq rate limit (429) — 30 RPM / 12K TPM / 100K TPD | High | Sequential calls; backoff retry once; then FAILED | Mock 429 |
| LLM-09 | Groq timeout / gateway error | High | Retry once; then FAILED | Simulate timeout |
| LLM-10 | Groq provider outage or daily quota exhausted | Critical | FAILED; ledger records error; Doc/email not attempted if before delivery | Provider down |
| LLM-11 | Quote valid under fuzzy match but not exact ( whitespace) | Low | Allow ≥90% similarity if configured | Extra spaces in quote |
| LLM-12 | Quote spans redacted `[PHONE]` placeholder | Medium | Valid if substring of scrubbed source text | Quote includes redaction |
| LLM-13 | LLM outputs unsafe/offensive action idea | Medium | No automated filter in v1; human review in staging; optional blocklist later | Toxic action text |
| LLM-14 | Re-prompt after quote failure exceeds token budget | Medium | Skip re-prompt; drop theme; continue if others valid | Tight budget + bad quotes |
| LLM-15 | Identical themes across consecutive weeks | Low | Allowed; recurring issues are signal; heading/week still unique | Same data window overlap |
| LLM-16 | LLM returns markdown/special chars in theme titles | Low | Sanitize for Docs plain text; strip control chars | Markdown in title |
| LLM-17 | Cluster excerpt truncated mid-sentence for token limit | Medium | Truncate at review boundaries (500 chars/review), not mid-character | Very long reviews |
| LLM-18 | Weekly run exceeds 10 Groq requests (5 themes + 5 re-prompts) | Medium | Should not happen in v1; log request count; cap re-prompts at one per cluster | Force all quote failures |

---

## 7. Report & Email Rendering

| ID | Scenario | Severity | Expected behavior | Test hint |
|---|---|---|---|---|
| REN-01 | Section heading format drift (manual code change) | Critical | Breaks idempotency; heading must match deterministic spec exactly | Compare heading bytes |
| REN-02 | ISO week spans month/year boundary in heading dates | Medium | Heading shows correct IST Mon–Sun range | Week at year boundary |
| REN-03 | Theme with zero quotes after validation | Medium | Omit quote bullets for theme; theme still listed if has title/summary | Quote-less theme |
| REN-04 | Zero themes in PulseReport reaches renderer | High | Should not happen; orchestrator fails earlier | Empty themes list |
| REN-05 | Very long theme title or action idea | Low | Truncate or wrap in Doc; email uses headlines only | 500-char title |
| REN-06 | Special characters in quotes (`"`, `'`, `&`) | Medium | Escape correctly in Doc blocks and HTML email | Quotes with symbols |
| REN-07 | `section_anchor_url` placeholder before Docs append | High | Email render deferred until URL known; or two-phase render | Render before docs |
| REN-08 | Email teaser includes full quotes (violates spec) | Medium | Teaser max ~15 lines; theme headlines only | Assert line count |
| REN-09 | Fewer than 3 themes; email bullet count | Low | Email shows 2 bullets if only 2 themes | 2-theme report |
| REN-10 | Re-render same PulseReport produces different hash | Medium | Must be deterministic (excluding timestamps in footer if excluded) | Double render compare |
| REN-11 | Doc block schema mismatch with Docs MCP | High | Validate payload against schema before MCP call | Invalid block type |
| REN-12 | HTML email without plain-text alternative | Medium | Multipart MIME with both bodies | Inspect raw message |
| REN-13 | CTA link broken or empty in email | Critical | Do not send if `section_anchor_url` missing/invalid | Null URL guard |
| REN-14 | Report footer timestamp timezone ambiguous | Low | Always ISO 8601 with `+05:30` IST offset | Check footer format |

---

## 8. Google Docs MCP

| ID | Scenario | Severity | Expected behavior | Test hint |
|---|---|---|---|---|
| DOC-01 | OAuth refresh token revoked / expired | Critical | 401 → refresh flow; if fails, clear error + FAILED run | Revoke token |
| DOC-02 | `docs_append_section` called twice same heading | Critical | Second call idempotent: `inserted: false`, same URL | Double append |
| DOC-03 | Heading exists but content differs (manual edit + `--force`) | High | Idempotent by heading only; `--force` full re-run policy must define replace vs skip | Manual doc edit |
| DOC-04 | Doc deleted or permission revoked mid-run | Critical | API 404/403; FAILED; log doc_id | Delete staging doc |
| DOC-05 | Doc approaching Google Docs size limit | Low | batchUpdate may fail; FAILED with size error; ops must archive old sections | Very long doc |
| DOC-06 | batchUpdate partial failure (API glitch) | High | Retry idempotent append; verify with `docs_find_section_by_heading` | Simulated partial write |
| DOC-07 | Heading text exists as body text elsewhere (false positive) | Medium | Match heading-level style or exact heading index; not plain paragraph | Duplicate text in doc |
| DOC-08 | Deep link / heading anchor not generated for new heading | High | Retry `docs_get_heading_link`; fail email if URL unavailable | New section link |
| DOC-09 | Concurrent append from two processes same week | Critical | One wins; second idempotent; no duplicate sections | Parallel runs |
| DOC-10 | Invalid `document_id` in config | Critical | Fail at MCP tool with clear 404 | Wrong doc_id |
| DOC-11 | Special Unicode in heading (en-dash vs hyphen) | High | Strict heading template; normalization must be consistent | Different dash chars |
| DOC-12 | Doc contains hundreds of weekly sections; find heading slow | Low | Acceptable latency; optional heading index cache in MCP server | Long history doc |
| DOC-13 | Service account vs user OAuth ownership mismatch | Medium | Doc must be writable by authenticated identity | Wrong sharing settings |
| DOC-14 | MCP server crash mid-batchUpdate | High | Orchestrator FAILED; retry safe via heading check | Kill MCP mid-request |

---

## 9. Gmail MCP

| ID | Scenario | Severity | Expected behavior | Test hint |
|---|---|---|---|---|
| GML-01 | Duplicate send same `run_id` | Critical | `gmail_find_by_idempotency_key` returns existing; no second message | Resend same week |
| GML-02 | Draft created then `send` requested same run | High | Idempotency on `X-Pulse-Run-Id`; define policy: draft counts as sent or upgrade draft | Draft → send |
| GML-03 | `X-Pulse-Run-Id` header stripped by relay | Medium | Idempotency key also in subject or internal ledger; document Gmail search limits | Search by header |
| GML-04 | Invalid recipient address | High | API error before send; FAILED email stage; Doc already appended | Bad email in config |
| GML-05 | Recipient mailbox full / bounce | Medium | Send API may succeed; bounces out of scope v1; log message_id | External bounce |
| GML-06 | Gmail API quota exceeded | High | Retry with backoff; FAILED if exhausted | Quota mock |
| GML-07 | OAuth scope insufficient | Critical | Fail at send with scope error at setup | Missing gmail.send |
| GML-08 | HTML-only body without text fallback | Medium | Always multipart per spec | Inspect MIME |
| GML-09 | Link in email blocked by client preview | Low | Plain-text URL duplicated; stakeholders copy-paste | Email client test |
| GML-10 | `--skip-email` flag | Low | No Gmail MCP call; ledger `gmail_message_id` null; COMPLETED still valid | Skip email run |
| GML-11 | `mode=draft` in production scheduler misconfigured | High | Draft only; stakeholders not notified; ops checklist | Wrong cron flag |
| GML-12 | Large recipient list (CC/BCC) | Low | v1: `to` only; ignore unsupported fields | Many recipients |
| GML-13 | Email subject line duplicate for different weeks | Low | Subject includes ISO week; unique per run | Compare subjects |
| GML-14 | Send succeeds but ledger write fails | High | Retry ledger update; email idempotency prevents duplicate on retry | Crash after send |

---

## 10. MCP Client & Orchestration

| ID | Scenario | Severity | Expected behavior | Test hint |
|---|---|---|---|---|
| MCP-01 | MCP server fails to start (bad Python path) | Critical | Orchestrator FAILED immediately; clear subprocess error | Break mcp.json command |
| MCP-02 | MCP tool schema change / missing tool | Critical | Fail at discovery; version lock MCP server + agent | Rename tool |
| MCP-03 | MCP stdio deadlock (large payload) | Medium | Timeout on MCP calls; FAILED with timeout message | Huge doc payload |
| MCP-04 | Only Docs MCP up; Gmail MCP down | High | Doc succeeds; email FAILED; partial recovery via `--from-stage email` | Stop Gmail server |
| MCP-05 | Agent imports Google API library by mistake | Critical | Architectural violation; CI import lint on `pulse/` | Static import check |
| MCP-06 | Two MCP servers share expired credentials independently | Medium | Each server refreshes own token; failures isolated | Expire one token |
| MCP-07 | `--dry-run` still spawns MCP servers | Low | Must not spawn/connect for delivery; optional connect for health check only | Dry-run MCP mock |
| MCP-08 | Orchestrator stage order violated via `--from-stage` | High | Validate stage prerequisites and artifact presence | Invalid stage jump |
| MCP-09 | Run exceeds 10-minute target on large corpus | Low | Log warning; do not fail; tune performance later | Timing metrics |
| MCP-10 | Zombie MCP child processes after parent crash | Medium | Shutdown hooks kill subprocesses; document cleanup | Kill parent only |

---

## 11. Idempotency, Ledger & Recovery

| ID | Scenario | Severity | Expected behavior | Test hint |
|---|---|---|---|---|
| IDM-01 | Ledger says COMPLETED but Doc section manually deleted | High | Re-run without `--force` exits 0 (wrong!); `--force` or ledger repair needed; Docs MCP finds no heading → re-append policy | Delete doc section |
| IDM-02 | Ledger FAILED; retry full run | High | Full pipeline rerun; no duplicate if partial delivery occurred | Retry after fail |
| IDM-03 | Ledger missing but Doc + email exist from manual run | Medium | Docs/Gmail idempotency layers still prevent dupes; ledger backfill optional | Delete ledger.db |
| IDM-04 | `--force` on COMPLETED week | High | Re-run full pipeline; Doc idempotent by heading; email idempotent by header; may refresh content if heading policy allows replace | Force same week |
| IDM-05 | Doc succeeded; ledger not updated; crash | High | Retry: heading exists → skip insert; complete ledger | Crash after doc |
| IDM-06 | Email succeeded; ledger not updated | High | Gmail idempotency prevents duplicate email on retry | Crash after email |
| IDM-07 | Three layers disagree (ledger PENDING, heading exists, email sent) | Critical | Reconciliation job or manual ops; prefer Gmail + Doc truth for delivery IDs | Corrupt state |
| IDM-08 | SQLite ledger locked (concurrent writes) | Medium | WAL mode; retry writes; avoid parallel same run_id | Parallel CLI |
| IDM-09 | `--from-stage email` but ledger says COMPLETED | Low | No-op exit 0 unless `--force` | Stage retry completed |
| IDM-10 | Partial FAILED state: which stage recorded | Medium | Ledger stores last successful stage or error_message for ops | Inspect FAILED row |
| IDM-11 | Backfill weeks out of order (W25 then W20) | Low | Each week independent; Doc sections append in run order not chronological | Out-of-order backfill |
| IDM-12 | Same ISO week run on two machines simultaneously | Critical | One completes; second idempotent at Doc + email layers; ledger race — use DB primary key constraint | Two schedulers |

---

## 12. Scheduling & Operations

| ID | Scenario | Severity | Expected behavior | Test hint |
|---|---|---|---|---|
| OPS-01 | Scheduler fires twice Monday 09:00 IST | Critical | Second run idempotent no-op | Double cron |
| OPS-02 | Scheduler runs under user without MCP auth | Critical | FAILED; auth path must match interactive setup | Task Scheduler user |
| OPS-03 | Machine asleep at scheduled time | Medium | Missed run; manual backfill `--week`; document ops procedure | Skip window |
| OPS-04 | DST not applicable (IST fixed) but server in UTC | High | All week math in `Asia/Kolkata` regardless of server TZ | UTC server |
| OPS-05 | Holiday Monday; stakeholders expect report anyway | Low | Ops decision: run still executes or pause schedule | Manual skip |
| OPS-06 | Local cache exceeds disk quota | Medium | FAILED on write; alert; retention cleanup | Fill disk |
| OPS-07 | 90-day cache retention deletes backfill source | Low | Old raw cache gone; re-export needs `--force-refresh` | Old run_id |
| OPS-08 | Production send before stakeholder sign-off | High | Process gate in Phase 8; staging draft default | Config promotion |
| OPS-09 | Groww app package renamed on Play Store | Critical | Update config; old package_id fails ingest | Package migration |
| OPS-10 | Weekly run during Play Store outage | High | Ingest retries then FAILED; use cached data if fresh enough? Policy: fail unless cache valid | Outage + no cache |

---

## 13. Security, Privacy & Abuse

| ID | Scenario | Severity | Expected behavior | Test hint |
|---|---|---|---|---|
| SEC-01 | PII leaked in published Doc or email | Critical | Scrub before all outputs; audit logs no raw PII | PII fixture E2E |
| SEC-02 | OAuth token committed to git | Critical | `.gitignore`; secret scan in CI | Gitleaks test |
| SEC-03 | Review text exfiltrated via Groq provider logging | Medium | Use provider terms; no PII in prompts beyond scrubbed text; `GROQ_API_KEY` env only | Provider policy |
| SEC-04 | Malicious review with script tags | Low | Strip HTML; plain text in Doc | XSS-like review text |
| SEC-05 | Extremely long review (DoS) | Medium | Truncate per-review char limit before embed/LLM | 50k char review |
| SEC-06 | Token/cost exhaustion attack (many huge reviews) | Medium | `max_tokens_per_run` cap; ingest volume limits | Cost cap test |
| SEC-07 | MCP server exposed on public HTTP without auth | Critical | v1: local stdio only; if HTTP, require auth | Network exposure audit |
| SEC-08 | Stakeholder email misaddressed (wrong domain) | High | Config review; test env uses internal addresses only | Typo in recipient |
| SEC-09 | Doc shared publicly instead of domain-restricted | High | Workspace sharing policy outside code; document in runbook | Manual sharing check |
| SEC-10 | Ledger or cache contains pre-scrub PII | Medium | Raw cache may contain PII; gitignored; retention limits | Inspect raw JSON |

---

## 14. Data, Storage & Concurrency

| ID | Scenario | Severity | Expected behavior | Test hint |
|---|---|---|---|---|
| DAT-01 | `data/reviews_normalized.json` missing on analyze-only run | Medium | Auto-run ingest or fail with instruction | Delete normalized file |
| DAT-02 | `data/report_{run_id}.json` manually edited with fake quotes | High | Re-validate quotes on render or delivery; or trust chain from analyze | Tampered report |
| DAT-03 | Corrupt SQLite ledger | High | Detect on open; backup/recreate; ops reconciliation | Corrupt db file |
| DAT-04 | Read-only filesystem for `data/` | High | FAILED with permission error | Read-only mount |
| DAT-05 | Windows path length limits for deep cache dirs | Low | Keep paths short; hash long run artifacts | Deep nesting |
| DAT-06 | Partial write to `reviews_raw.json` or `reviews_normalized.json` (crash mid-write) | Medium | Atomic write (temp + rename); detect invalid JSON on load | Kill during write |
| DAT-07 | Embedding cache from different model version | Medium | Cache key includes model name (`BAAI/bge-small-en-v1.5` or `bge-large`); path `embeddings_{run_id}.parquet` | Swap model in `pulse.yaml` |
| DAT-08 | Audit payload hash mismatch on `--force` re-run | Low | New hash recorded; old hash in ledger history if versioned | Force re-run |

---

## Cross-Cutting Scenarios

| ID | Scenario | Severity | Expected behavior | Test hint |
|---|---|---|---|---|
| X-01 | End-to-end success path (happy path) | — | COMPLETED ledger; Doc section; email sent/draft; audit JSON | Full staging run |
| X-02 | End-to-end with `--dry-run` | — | All artifacts local; no MCP side effects | Dry-run |
| X-03 | v1 scope violation: user requests App Store | — | Out of scope; reject at design; no code path | N/A |
| X-04 | Report quality rejected by stakeholders | — | Tune clustering/LLM in Phase 8; not an automated edge case | Manual review |
| X-05 | Week-over-week identical themes (rolling 12-week window) | Low | Expected overlap; headings differentiate weeks | Compare consecutive weeks |

---

## Priority Matrix for Testing

Implement automated or manual tests in this order:

| Priority | IDs | Rationale |
|---|---|---|
| P0 — Must test before production | ING-04, LLM-01, LLM-02, DOC-02, GML-01, IDM-01, IDM-12, SEC-01, REN-13 | Delivery correctness, idempotency, security |
| P1 — Before staging sign-off | ING-01, CLU-01, LLM-06, LLM-08, DOC-01, GML-04, MCP-04, RUN-05, PRE-06, CFG-11 | Failure recovery and partial paths |
| P2 — Hardening | Remaining Medium/Low items | Polish and ops resilience |

---

## Edge Case → Architecture Mapping

| Document section | Edge case IDs |
|---|---|
| [Failure Handling](./architecture.md#failure-handling) | ING-01, ING-04, CLU-01, LLM-08, LLM-09, DOC-01, GML-06 |
| [Idempotency & Run Ledger](./architecture.md#idempotency--run-ledger) | DOC-02, GML-01, IDM-01 – IDM-12, RUN-05 |
| [Security, Privacy & Quality](./architecture.md#security-privacy--quality) | PRE-*, SEC-*, LLM-01 |
| [MCP Servers](./architecture.md#mcp-servers) | DOC-*, GML-*, MCP-* |
| [Phase 7 — Idempotency](./implementation-plan.md#phase-7--idempotency-run-ledger--audit) | IDM-*, RUN-08, RUN-09 |
| [Risk Register](./implementation-plan.md#risk-register) | ING-01, CLU-01, LLM-02, DOC-01, GML-01, IDM-* |

---

## Related Documents

- [ProblemStatement.md](./ProblemStatement.md) — Scope and delivery expectations
- [architecture.md](./architecture.md) — Technical design and failure handling
- [implementation-plan.md](./implementation-plan.md) — Phased build plan and acceptance criteria
