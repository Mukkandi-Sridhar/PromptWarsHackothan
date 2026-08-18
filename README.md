# SIGNAL — Reel Intelligence Agent

An agent that reads what a student's scrolling actually means, and redirects the next 60 seconds toward something worth their time.

**The goal is not to stop social media use. It is to make existing scrolling useful.**

---

## Problem Statement Alignment

### The trap, and how SIGNAL defeats it

A student watches a Java meme, an SWE lifestyle reel, a coding-interview joke, and a laptop comparison. A shallow system sees the token `java` and serves another Java meme. It also happily serves *"10 AI Tools That Will Get You a Job"*, because that content looks relevant and performs well.

SIGNAL defeats this with two mechanisms:

**1. The Abstraction Ladder — inference, not keyword matching.**

Every watched reel is decomposed into three levels:

| Level | Meaning | Example |
|---|---|---|
| **L1 · Surface tokens** | What the reel literally says | `java`, `nullpointerexception`, `macbook` |
| **L2 · Skill domains** | The transferable field underneath | Backend Engineering, Interview Technique |
| **L3 · Identity & goals** | Who the student is becoming | *Becoming a software engineer · placement anxiety* |

Convergence is computed across reels. **Recommendations are generated from L2 children of the converged L3 node — never from an L1 sibling of the current reel.** That single rule is what separates topic inference from keyword matching.

**2. The Substance Gate — hype is rejected, visibly.**

Every candidate is scored 0–100 on specificity, transferability, verifiability, shelf life, actionability, and creator grounding, with penalties applied:

| Penalty | Weight | Example trigger |
|---|---|---|
| Outcome promise | −35 | "will get you a job", "land ₹X LPA" |
| Tool listicle, no concept | −30 | "10 AI tools that…" |
| Manufactured secrecy | −20 | "nobody tells you this" |
| Unfalsifiable claim | −15 | "10x your package" |

Threshold is 60. Rejections are **surfaced in the UI with the score and the triggering phrase**, not silently filtered. `10 AI Tools That Will Get You a Job in 2026` scores 22 and is visibly blocked.

**3. Blocking on lift, not on topic.**

The failure mode in the brief is another *generic* Java reel. The sin is the absence of lift, not the topic. A same-topic candidate is allowed only if it clears substance ≥ 70, steps up in difficulty, and has under 60% concept overlap with what was already watched.

Result on the trap scenario: SIGNAL recommends *"Your NullPointerException isn't a bug, it's a design decision"* — a Java reel teaching `Optional` — while blocking six other Java reels that offered no lift.

### Discrimination, not reaction

Reels 5, 6 and 8 (street food, mobile gaming, generic motivation) are negative-evidence cases. A skip under 3 seconds carries **negative** weight. When the current reel contributes nothing, the output states so explicitly and the interest graph is left unchanged — the agent does not start recommending recipes.

### Required output format

Produced verbatim, in this order:

```
CURRENT REEL:            NullPointerException hits different at 2am
INTEREST DETECTED:       Becoming a software engineer · placement anxiety,
                         expressed as Backend Engineering
WHY:                     Evidence from 4 reels with 3 converging signals across
                         identity affirmation, aspiration and anxiety relief
RECOMMENDED TECH REEL:   Your NullPointerException isn't a bug, it's a design decision
CATEGORY:                Java
WHY THIS RECOMMENDATION: Shares the emotional entry point of content already
                         enjoyed while delivering a transferable concept one step
                         above demonstrated sophistication
DIFFICULTY:              Intermediate
CONFIDENCE:              High
```

**Confidence is calibrated, not decorative.** Three or more converging reels → High. Two → Medium. One or contradictory intents → Low, and the recommendation deliberately widens rather than guessing.

**Filter bubbles are addressed.** One labelled exploration slot recommends from an adjacent domain the student has never watched.

---

## Architecture

Seven stages, each streamed to the UI over SSE so the reasoning is inspectable in real time.

```
S1  Semantic decomposition   surface topic → latent concepts → intent signal
S2  Interest graph           L1/L2/L3 synthesis, convergence, latent need
S3  Retrieval                composed query vector, de-biased away from L1
S4  Substance gate           all candidates scored; hype rejected with reasons
S5  Echo filter              low-lift same-topic candidates removed
S5b Fit ranking              alignment · bridge fit · latent need · novelty · engagement
S6  Calibration              difficulty = current sophistication + 1; confidence rules
S7  Explanation              required output block + full reasoning trace
```

**Stack:** FastAPI · Pydantic v2 · SQLAlchemy/SQLite · OpenAI (structured outputs, strict JSON schema) · React 18 + TypeScript + Vite · Framer Motion.

---

## Efficiency

- **Precomputation.** Reel decompositions and candidate substance scores are computed once at seed time and cached by content hash. Only session-dependent stages (S2, S7) run per request — 36 calls per interaction reduced to 2.
- **Batched scoring.** Candidates are scored ten per call as a JSON array. Roughly 10× faster than sequential calls, and scores are more consistent because the model compares candidates against each other rather than estimating in isolation.
- **Parallelism.** `asyncio.gather` with a semaphore capped at 8. No `await` inside loops.
- **Retrieval** is cosine similarity over precomputed vectors — O(n) numpy, ~2ms.
- **Response caching** keyed on `(stage, model, prompt)`. Repeat runs are instant and free.
- **Frontend:** animations are restricted to `transform` and `opacity`. Candidate particles render in a single layer, not per-component. 60fps on integrated graphics.

---

## Testing

```bash
pytest backend/tests/ -v
```

| Test | Asserts |
|---|---|
| `test_no_shallow_echo` | Recommendation is never a low-lift L1 sibling |
| `test_bridge_wins` | The trap scenario returns the design-decision reel |
| `test_hype_rejected` | "10 AI Tools…" scores <40 and appears in `rejected[]` |
| `test_l3_convergence` | SWE identity reaches High after reels 1–4 |
| `test_negative_signal` | Street-food reel contributes zero or negative weight |
| `test_weak_signal_ignored` | Low-engagement motivational reel never dominates |
| `test_low_confidence_widens` | Single-reel session yields Low and a broader pick |
| `test_output_format` | Eight lines, exact labels, exact order |
| `test_offline_parity` | Valid recommendation with no network |

Every stage has a deterministic reference implementation, so the full pipeline is testable without network access or API cost.

---

## Security

- No secrets in source. `OPENAI_API_KEY` is read from environment; the startup log records key **presence**, never any part of the value.
- Every LLM response is validated against a strict Pydantic schema before use. Malformed output falls back rather than propagating.
- Structured outputs with `strict: true` constrain the model to the declared schema.
- Parameterised queries throughout via SQLAlchemy — no string-built SQL.
- CORS restricted to the known frontend origin.
- Per-session API call budget (60) prevents runaway cost from a loop.
- Unhandled exceptions return a typed JSON error and are logged server-side; internal identifiers are never rendered in the UI.

---

## Accessibility

- Full keyboard navigation: arrow keys advance the feed, space pauses, tab order follows visual order, focus is always visible.
- `prefers-reduced-motion` collapses all animation to opacity fades; the app remains fully functional.
- Body text meets WCAG AA contrast against panel backgrounds; no information is conveyed by colour alone — every rejection carries a text reason alongside its colour.
- Semantic markup: the required output block is a `<dl>`, panels use landmark roles, all icon-only controls carry `aria-label`.
- Live regions announce pipeline stage changes to screen readers.
- No autoplaying audio.

---

## Code Quality

- Each pipeline stage is an isolated module with a single responsibility and a typed interface (`s1_decompose.py` … `s7_explain.py`).
- Pydantic models are the contract between backend, LLM, and frontend — one schema definition, no drift.
- Provider-agnostic LLM client; swapping providers touches one file.
- Deterministic fallback per stage, with the reason recorded in the trace and surfaced honestly in the UI (`gpt` · `hybrid · S4 offline` · `offline · <reason>`).
- Structured logging via `structlog`.
- Frontend state centralised in Zustand; in-flight requests cancelled via `AbortController` so rapid interactions cannot interleave.

---

## Running it

```bash
git clone https://github.com/Mukkandi-Sridhar/PromptWarsHackothan.git && cd PromptWarsHackothan/signal
./run.sh          # installs, seeds, precomputes, starts both servers
```

Frontend on `:5173`, API on `:8000`. Runs fully offline without an API key — the UI reports which mode it is in.

---

## Demo

1. **Shallow Mode**, reels 1–4 → another Java meme and an AI-tools listicle. Relevant, and worthless.
2. **Agent Mode**, same reels → the ladder climbs L1 → L3. Four reels, one conclusion.
3. **Hype Shield** → the AI-tools reel was found and thrown out. Outcome promise, no transferable concept.
4. **Recommendation** → it stayed on Java, on purpose, and blocked six other Java reels. The difference is not the topic. It is whether the next sixty seconds teach you something.
5. **Street food reel** → no signal, graph unchanged. It did not start recommending recipes.

Out of 30 topically relevant candidates retrieved, 11 were rejected on substance and lift.

**Relevance was never the hard part.**
