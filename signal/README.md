# SIGNAL — Reel Intelligence Agent

> Reads what a student's scrolling *actually means* and redirects the next 60 seconds toward something worth their time.

---

## Setup

```bash
git clone <repo>
cd signal
./run.sh
```

Open **http://localhost:5173**

That's it. No Docker. No API keys required (runs fully offline in deterministic mode).

### Optional: Enable LLM mode

Copy `.env.example` to `.env` and set your key:

```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

The system detects the key and switches from deterministic to LLM mode automatically. If wifi dies mid-demo, it falls back to deterministic with a visible `offline model` badge — the output stays valid.

---

## Architecture

```
┌─ 7-Stage Agent Pipeline ─────────────────────────────────┐
│ S1 Decompose   → semantic layers from each reel           │
│ S2 Graph       → L1/L2/L3 abstraction + convergence       │
│ S3 Retrieve    → composed query (anti-trap vector)        │
│ S4 Substance   → score + reject hype before ranking       │
│ S5 Rank        → bridge_fit + latent need + novelty       │
│ S6 Calibrate   → confidence with stated uncertainty       │
│ S7 Explain     → 8-line verbatim output + full trace      │
└───────────────────────────────────────────────────────────┘
```

**The Abstraction Ladder** — the core insight:
- L1 (surface): "Java", "MacBook", "interview"  
- L2 (skills): Backend Engineering, Interview Technique, Hardware Selection  
- L3 (identity): "Becoming a software engineer · placement anxiety"  

Recommendations come from L2. Never from L1. The ladder is animated on screen.

**Substance Gate** — every candidate is scored 0–100 on six dimensions before it can be recommended. Hype reels are rejected with named reasons: "Blocked — outcome promise −35". That rejection is shown, not hidden.

---

## Tests

```bash
cd signal
source .venv/bin/activate
pytest backend/tests/test_agent.py -v
```

All 8 tests pass. They verify:
1. No L1 echo recommendations (anti-trap)
2. Hype reel scores < 40, rejected with `outcome_promise` penalty
3. L3 convergence reaches High confidence after 4 SWE-identity reels
4. Street food reel (skipped at 4s) contributes zero graph weight
5. Motivational grind reel does not dominate
6. Single reel → Low confidence → explicit widening message
7. 8-line output in exact order with exact labels
8. Deterministic (offline) mode produces valid recommendation end-to-end

---

## 90-Second Demo Script

**Setup:** Open http://localhost:5173 in a browser. The app starts in Agent Mode.

---

### Beat 1 — (0:00) Shallow Mode first

1. Flip the toggle at the top to **Shallow Mode** (label turns red: "keyword match only")
2. Swipe through reels 1–4: Java meme → SWE day-in-life → linked-list panic → MacBook comparison
3. Click **▶ Analyze session**
4. Point to the recommendation card: it surfaces another Java reel and the "10 AI Tools" listicle

*"This is what keyword matching gives you. Relevant. And worthless."*

---

### Beat 2 — (0:30) Flip to Agent Mode

5. Toggle back to **Agent Mode**
6. Click **▶ Analyze session** again
7. Watch the **Abstraction Ladder** animate:
   - L1 tokens drop in: Java, MacBook, interview
   - Lines climb to L2: Backend Engineering, Interview Technique, Hardware Selection
   - L3 ignites in amber: *"Becoming a software engineer · placement anxiety"*

*"Four reels. The system reads them as one thing: someone becoming a software engineer, worried about placements."*

---

### Beat 3 — (0:50) Hype Shield lights up

8. Point to the **Hype Shield** panel (coral border, struck-through titles)
9. Hover over "10 AI Tools That Will Get You a Job in 2026" — the flagged phrase highlights
10. Read out the rejection: *"Blocked — outcome promise −35, tool listicle −30. Final score: 22"*

*"It found the AI-tools reel too. It rejected it — outcome promise, no transferable concept. Rejection is a feature we show, not a filter we hide."*

---

### Beat 4 — (1:05) Recommendation fills

11. Point to the **Recommendation Card**
12. Read the verbatim 8-line output block:
    - INTEREST DETECTED: Becoming a software engineer, expressed as Interview Technique
    - RECOMMENDED: "Reverse a linked list — the pointer dance, drawn out"
    - DIFFICULTY: Beginner
    - CONFIDENCE: High

*"Same joke it already likes. Real concept underneath. One step up, not five."*

13. Point to the serendipity pick: "How your login session gets stolen" — labeled "Exploration: adjacent domain"

---

### Beat 5 — (1:20) Live graph update

14. Press **Save** on any reel in the feed
15. Watch the **Interest Graph** shift — the saved node's L2 weight increases
16. Click **▶ Analyze session** — the graph updates and confidence may rise

*"It keeps learning. We're not trying to stop the scrolling — we're taxing it."*

---

## Two Lines for When Judges Push Back

**"Isn't this just a recommender?"**  
A recommender optimizes for the next watch. This optimizes for whether the next watch was worth it, and it will refuse to recommend rather than recommend something hollow. Different objective function.

**"How do you know the inference is right?"**  
We don't always, so the system says so. Confidence is derived from signal convergence, and at Low confidence it deliberately widens instead of guessing. Overconfidence is the failure mode we designed against.

---

## The Metric for Your Final Slide

> Out of 48 candidates retrieved as topically relevant, 9 were rejected on substance.  
> Relevance was never the hard part.
