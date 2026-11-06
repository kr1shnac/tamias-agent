---
name: council
description: Run a "council" to stress-test a decision, plan or whole project. Five independent advisors with different thinking styles (Contrarian, First Principles, Expansionist, Outsider, Executor) answer the same neutrally framed question in isolated subagents; five reviewers anonymously cross-review them (strongest, biggest blind spot, what all five missed); a chairman delivers a verdict with one concrete next step. Use whenever the user says "council this", "run the council", "LLM council", "second opinion", "stress-test this", "review the whole project", or faces a costly fork or a plan they want challenged rather than flattered. Skip for simple factual questions or when the user only wants validation.
---

# Council

**Version:** v1.3 (2026-10-20). Adds section 19 (add-ons for exhaustive
whole-repo verification runs). v1.2 added section 17 (repo/service audit
add-ons). v1.1 added section 15 (build/keep/kill add-ons). The core method, rules
and prompts in sections 1–14 are unchanged. There is no section 16; the
numbering gap is historical and kept rather than renumbered, so that section
numbers cited in earlier run records still resolve to the same text.

## 1. What this skill does

One model asked one question tends to agree with whoever framed it. The council counters that by forcing several independent perspectives onto the same question, letting them criticize each other without knowing who wrote what, and then synthesizing a verdict.

Pipeline (method: Ole Lehmann's five-advisor council, built on Andrej Karpathy's LLM Council):

1. **Frame** the question neutrally and attach the real materials.
2. **Five advisors** answer in parallel, each in an isolated context, each with a different thinking style.
3. **Anonymize** the answers (real random shuffle, labels A-E).
4. **Five reviewers** read all five anonymous answers and answer three questions: which is strongest, which has the biggest blind spot, what did all five miss.
5. **Chairman** reads everything and returns a verdict, the disagreements, and **one concrete next step**.
6. **Report**: markdown transcript plus a single-file HTML report.

The "what did all five miss" question is the most valuable one. Keep it.

## 2. When to use it

Use it for decisions or reviews where being wrong is expensive: product or architecture forks, "should we pursue X", pricing, positioning, hiring, a plan the user keeps going back and forth on, or "review this whole project and list every issue".

Do not use it for factual lookups, small coding tasks, or when the user already decided and only wants validation. Say so briefly instead of running it. The council will tell people things they may not want to hear; that is the point.

## 3. Non-negotiable rules

These exist because a previous run broke them (see section 12).

1. **Isolation.** Every advisor, reviewer and the chairman is a separate subagent or session with fresh context. It receives only the prompt text defined in this skill, never the main conversation and never your own opinions. Advisors never see each other's answers.
2. **Neutral framing.** The framed question must not contain your conclusions, a preferred option, a list of "known problems", or loaded adjectives. Put the user's words and evidence in verbatim. If there are options, state them symmetrically and add "something else / none of these".
3. **Real anonymization.** Shuffle with a real random generator in code, save the mapping to a file, and never show reviewers names or the mapping.
4. **Never write a role's output yourself.** If you cannot spawn isolated subagents or sessions, stop and tell the user. Only if the user agrees, run a clearly labelled simulation and mark the whole report "SIMULATION: roles are not independent; rankings carry no evidential weight."
5. **Never fabricate votes.** Parse what actually came back. Drop failed members and record the drop.
6. **Tag claims.** `[FACT]` verified with a tool this run, `[MATERIALS]` stated in the provided materials but not verified, `[INFERENCE]` reasoning, `[OPINION]` judgement. Say "unverified" whenever it applies. Never invent numbers, sources or quotes.
7. **No flattery, no false balance.** Advisors disagree where they disagree. The chairman preserves minority views instead of averaging them away.
8. **Read-only advisors.** Advisors, reviewers and chairman may read files and search the web if allowed. They must not edit files, run state-changing commands, or call external services with side effects.
9. **Secrets.** When scanning the workspace, never read or include `.env`, credentials, private keys, tokens or key files. If the materials contain secrets, redact them and tell the user.

## 4. Inputs and defaults

| Input | Default | Meaning |
|---|---|---|
| `question` | the user's words, verbatim | What to decide or review |
| `materials` | auto-detected | Files or folders to include (README, AGENTS.md, docs, briefs, specs) |
| `mode` | `styles` | `styles` (five thinking styles), `models` (N different models, same plain question), `both` (styles, each on a different model) |
| `depth` | `standard` | `quick` (150-250 words per advisor), `standard` (300-500), `deep` (600-900) |
| `project_review` | auto | On when the user asks to review a whole project; adds section 6.3 and the issue register |
| `search` | off unless needed | Allow web search for current facts; findings are added to the materials as `[FACT]` with source |
| `models` | all the same | Optional map advisor to model; use different models when several providers are configured |

If the question is ambiguous, ask at most one clarifying question. Otherwise restate the decision neutrally and proceed.

## 5. Workflow

### Step 0: Collect materials
Read the user's files and, if relevant, `AGENTS.md`, `README`, `docs/`, notes. Include material verbatim or as exact excerpts plus a file list. Do not summarize in your own words and do not add commentary; summaries smuggle in your opinion. If material is too large, include the most relevant verbatim sections and list the rest by path so advisors can read them with tools. Skip secrets (rule 9).

### Step 1: Frame
Write `framed-question.md` with exactly these sections:

```
## Decision
<one or two neutral sentences: what is being decided or reviewed>

## Options
<the real options, stated symmetrically, plus "something else / none">

## Constraints and context given by the user
<verbatim quotes of what the user said; nothing added by you>

## Materials
<verbatim excerpts with file paths>

## Current facts (only if search was used)
<findings with source links, labelled [FACT]>
```

Checklist before sending: no conclusion, no preferred option, no list of flaws, no adjectives like "weak" or "promising", options equally detailed. If you caught yourself leaning, rewrite. Show the user the Decision and Options sections and the cost estimate (section 10); proceed unless they object, or in non-interactive runs, proceed.

### Step 2: Advisors (parallel, isolated)
Spawn five subagents in a single batch so they run in parallel. Each receives the prompt from 6.1 + its persona from 6.2 + the framed question (+ 6.3 if project review). Collect the five responses. Retry a failed advisor once; need at least three to continue.

### Step 3: Anonymize
Write the five responses to files by style. Remove self-identification ("As the Contrarian...") from the text by replacing it with "[advisor]". Shuffle with real randomness, for example:

```
python3 -c "import random,json;s=['contrarian','first_principles','expansionist','outsider','executor'];random.shuffle(s);print(json.dumps(dict(zip('ABCDE',s))))" > mapping.json
```

Build `responses_text` as blocks `Response A:\n<text>` separated by a blank line.

### Step 4: Peer review (parallel, isolated)
Spawn five fresh reviewers. Each receives only the prompt in 6.4 with `{framed_question}` and `{responses_text}` filled in. Every reviewer sees all five responses, including the one it would have written. Keep each raw review. Parse the rankings (section 7).

### Step 5: Chairman (one fresh subagent, strongest available model)
Send only the prompt in 6.5. It gets the framed question, the five advisor responses with their real style names, the five raw reviews with anonymous labels, and the label-to-style mapping. Retry once on failure; if it still fails, deliver the raw stages and say synthesis failed.

### Step 6: Spot-check
You (the orchestrator) check the three to five highest-impact claims in the chairman's answer that a tool can verify (grep the repo, run a test, fetch a page). Record results in `verification.md` as confirmed, contradicted or unverifiable, and mark the final answer accordingly. Never silently fix a contradicted claim; show it.

### Step 7: Deliver
Write the files in section 8 and give the user the short chat summary.

## 6. Prompt library (use these texts as written)

### 6.1 Advisor wrapper

```
You are one advisor on a council. Several advisors will answer the same question independently; you will not see the others. Answer from your assigned thinking style only.

Rules:
- Be specific and evidence-based. Cite the materials by file or section.
- Tag each substantive claim [FACT], [MATERIALS], [INFERENCE] or [OPINION]. Say "unverified" when it applies. Never invent numbers, quotes or sources.
- Give a confidence (High / Medium / Low) for each major claim.
- Do not hedge to be agreeable. Disagree with the framing if it is wrong.
- Length: {length_words} words.
- End with one line: "One-line verdict: ..."

Your thinking style:
{persona}

The question:
{framed_question}
```

### 6.2 The five personas

**Contrarian**
```
Assume the idea, plan or project has a fatal flaw and find it. Look for what will fail, what is overclaimed, what evidence is missing, and what the author is too close to see. If everything looks solid, dig deeper and name the most likely way it fails anyway. Do not soften. Only propose a fix when it directly removes a flaw you found.
```

**First Principles Thinker**
```
Ignore how the question is phrased and ask what is actually being solved. List the assumptions hidden in the framing and challenge each one. Rebuild the problem from the ground up: what would you do starting from zero? Say whether the question is optimizing the wrong variable.
```

**Expansionist**
```
Hunt for upside that is being missed. What could be bigger? What adjacent opportunity sits right next to this that nobody mentioned? What cheap experiment would test it? Stay grounded: tie every upside to something in the materials, and say what would have to be true for it to work.
```

**Outsider**
```
You have zero context about this person, their field, their history or their jargon. Respond only to what is literally in front of you. Say what you do not understand, what is assumed but never explained, and what a newcomer, customer or buyer would not get. Do not use outside knowledge of this project. Treat every unexplained term as unexplained.
```

**Executor**
```
You care about one thing: what happens on Monday morning. For each recommendation, give the first concrete action, what it needs, how long it takes, and how you would know it worked. If an idea has no clear first step, say so plainly. End with a sequenced plan for the next one to two weeks and the one thing you would deliberately not do yet.
```

### 6.3 Project-review coverage checklist (add when `project_review` is on)

Append to every advisor's prompt:

```
This is a whole-project review. Beyond your style, cover each area below. For each area give specific issues with evidence, or write "no view" if you genuinely have none. Do not skip an area silently.
Areas: architecture and design; correctness and testing; security and trust model (enumerate how it can be bypassed and what the real guarantee is); operations and reliability; product and first-use experience; research or evidence validity (what is measured, what is not, is the sample size enough); commercial viability (buyer, budget, competitors, distribution); legal and compliance (claims, licensing, privacy); and what is missing from the materials entirely.
```

### 6.4 Reviewer prompt

```
You are a reviewer on a council. Below is a question and five anonymous responses (A to E) from different advisors. You do not know who wrote what.

Question:
{framed_question}

Responses:

{responses_text}

Answer exactly these three questions, in this order, in plain text:

1. Which response is the strongest, and why? Cite specific points.
2. Which response has the biggest blind spot? Name the response and the blind spot.
3. What did ALL FIVE responses miss? Be specific. Do not repeat anything any response already said. If nothing material was missed, say so and explain why.

Then, at the very end, give a final ranking from best to worst in exactly this format:

FINAL RANKING:
1. Response X
2. Response Y
3. Response Z
4. Response V
5. Response W

Do not add any text after the ranking.
```

### 6.5 Chairman prompt

```
You are the Chairman of a council. Five advisors, each with a different thinking style, answered the question below independently. Five reviewers then read the anonymized answers, named the strongest and the biggest blind spot, and listed what all five missed.

Question:
{framed_question}

STAGE 1: Advisor responses (named by style):
{stage1_text}

STAGE 2: Reviews (the reviewers used anonymous labels; the mapping is given here):
{mapping}

{stage2_text}

Write the council's final answer. Rules:
- Do not invent evidence. Keep the [FACT] / [MATERIALS] / [INFERENCE] / [OPINION] tags and mark anything unverifiable.
- Preserve minority views and say who held them. Do not average disagreement away.
- Give special weight to what reviewers said all five missed.
- Be direct. No flattery, no hedging for politeness.

Use exactly this structure:

VERDICT: <one line>
CONFIDENCE: High | Medium | Low, and why
WHERE THE COUNCIL AGREED:
WHERE IT SPLIT (keep dissent):
WHAT PEER REVIEW CAUGHT THAT NO ADVISOR SAID:
KEY RISKS AND UNKNOWNS:
RECOMMENDATION:
ONE CONCRETE NEXT STEP: <a single action doable within one working day, plus the check that tells you it worked>
WHAT WOULD CHANGE THIS VERDICT:

If this is a whole-project review, also add an ISSUE REGISTER table with columns:
ID | Severity (Critical/High/Medium/Low) | Issue | Evidence (file or section, or "advisor claim, unverified") | Fix | Done when | Raised by
```

## 7. Parsing and aggregation

- Parse each review after the first `FINAL RANKING:`: take lines matching `digits. Response <capital letter>`, in order. If none match, take every `Response <letter>` after the marker, in order. If there is no marker, take every `Response <letter>` in the whole text, in order. Record any fallback used.
- Aggregate: for each response, average its position across all parsed rankings (self-votes included, as in the original method) and count votes. Lower is better.
- Also tally: how many reviewers named each response strongest, and each biggest blind spot.
- Rankings are advisory. Never present the aggregate as proof; the arguments matter more than the votes.
- After aggregation, reveal the mapping in the report.

## 8. Output

### 8.1 Files
Create `.council/runs/<YYYYMMDD-HHMM>-<short-slug>/` containing:

```
framed-question.md
advisors/<style>.md                 (5 files)
reviews/reviewer-<1-5>.md           (raw text + parsed ranking)
mapping.json
aggregate.md                        (ranking table, strongest and blind-spot tallies)
chairman.md
verification.md                     (section 5, step 6)
transcript.md                       (everything above in reading order)
report.html                         (single self-contained file, no external requests)
```

### 8.2 report.html
Self-contained, light and dark mode via CSS variables, readable on a phone, scannable in 60 seconds. Top to bottom: verdict card (verdict, confidence, one next step); issue register (project reviews); where the council agreed and split; "what all five missed"; five advisor cards with anonymous letter badges and style revealed; a review matrix (rows reviewers, columns strongest, blind spot, ranking); aggregate table; verification results; limits and run notes (mode, models, dropped members, simulation flag). No remote fonts, scripts or images.

### 8.3 Chat summary
At most 150 words: the verdict line, confidence, the one concrete next step, the path to `report.html` and `transcript.md`, and run notes (dropped members, simulation or not, estimated tokens). Offer the full raw outputs of any stage.

## 9. Modes

- **styles** (default): five thinking styles, ideally on different models if several are configured.
- **models** (Karpathy original): three to five different models answer the same plain question with no persona; stages 3 to 5 are identical. The reviewer prompt in 6.4 works unchanged. Use the chairman from the strongest model.
- **both**: styles, each style assigned a different model. Most diversity.

If only one model is available, say that disagreement will be smaller. Do not pretend otherwise.

## 10. Failure handling and cost

- Advisor fails: retry once, then drop; continue with three or more. Fewer than three: stop and say so.
- Reviewer fails: drop it and note it. Chairman fails: retry once, otherwise deliver raw stages.
- Context too large: cut materials to verbatim excerpts plus file paths and tell the user.
- Cost estimate: calls = 5 + 5 + 1 = 11. Input tokens are roughly `5*M + 5*(M+R) + (M+R+V)` where M is the framed question plus materials, R the five advisor answers (about 2-3k) and V the five reviews (about 2-3k). Show the estimate before running when M exceeds about 15k tokens, and offer: `quick` depth, a cheaper model for advisors and reviewers with the strongest model only as chairman, or narrowing the question to one fork.

## 11. Quality checklist before delivering

- [ ] Framed question had no conclusions or loaded wording
- [ ] Every role ran in a fresh isolated context (or the report is marked SIMULATION)
- [ ] Letters were shuffled with real randomness; mapping saved; reviewers never saw it
- [ ] No votes or answers were written by the orchestrator
- [ ] Rankings parsed from actual output; fallbacks and drops recorded
- [ ] Chairman's checkable claims were spot-checked
- [ ] The verdict ends in exactly one concrete next step
- [ ] Unverified items are labelled as such

## 12. Lessons from a prior single-model simulation (do not repeat)

An earlier council was written entirely by one model in one pass. Problems to avoid:
1. The framed question listed "what is not built" and quoted the claim under review, which leaked conclusions into the question.
2. Advisors were written after the author had already formed a view, so their agreement was an echo.
3. The rankings and tally were authored, not collected, so they carried no information.
4. Some of the "all five missed" items were the author's own additions, not discoveries.
5. The arguments were still checkable against the materials; judge by evidence, not votes.

## 13. OpenCode implementation notes (illustrative; verify against the current OpenCode docs)

- **Skill location:** `.opencode/skills/council/SKILL.md` (project) or `~/.config/opencode/skills/council/SKILL.md` (global). The directory name must equal `name`; `description` must be 1-1024 characters. The skill is loaded with OpenCode's `skill` tool.
- **Subagents:** define `council-advisor`, `council-reviewer` and `council-chairman` as subagents in `.opencode/agents/` with read-only permissions (no edit, no write-capable bash). Set a different `model` per subagent when you want model diversity.
- **Parallelism:** issue all five advisor tasks in one assistant message, then all five reviewer tasks in one message. If parallel subagents are not available, run each role as a separate fresh session (for example one non-interactive CLI invocation per role) so contexts stay isolated; never reuse a session between roles.
- **Slash command (optional):** `.opencode/commands/council.md` with a short description and a template that says: load the `council` skill and run it on `$ARGUMENTS`.
- **Randomness and files:** use a small script or one-liner for the shuffle and for assembling `responses_text`, so you do not do it by hand.
- Illustrative subagent frontmatter (key names may differ in the current version):

```
---
description: Council advisor. Answers one framed question from one assigned thinking style. Read-only.
mode: subagent
model: <provider/model>
permission:
  edit: deny
  bash: deny
---
Follow the prompt you are given exactly. Do not ask questions. Do not use any context except what is in the prompt and files you are told to read.
```

## 14. Honest limits

- A council of copies of one model disagrees less than a council of different models. Use `models` or `both` when several providers are configured.
- Agreement is not truth. The council improves coverage and exposes blind spots; it does not verify facts. Spot-check (section 5, step 6) matters.
- Reviewer rankings are noisy. Treat them as a signal about which arguments held up, not as a vote count that decides.
- The method works best on one clear decision with real materials. Vague questions give vague councils.

## 15. Add-ons for build / keep / kill decisions

Use these when the question is "should this thing exist at all, and if so what
scope" — a new product, feature, repo, or a plan the user may cancel. They add
to sections 1–14; they never replace the non-negotiable rules in section 3.

### 15.1 Claim grading (search on by default)

Set `search` on. Every substantive claim gets one of:

- `[FACT]` verified with a tool this run (URL fetched, file read, test run)
- `[VENDOR-CLAIM]` a company's or project's own number, not independently measured
- `[MATERIALS]` stated in the provided materials but not verified here
- `[INFERENCE]` reasoning from the above
- `[OPINION]` judgement

Competitor or vendor performance numbers ("saves 30–40%") are `[VENDOR-CLAIM]`
unless a tool in this run shows an independent measurement. Never repeat a
vendor number as if it were a fact.

### 15.2 Two-part verdict (existence before scope)

The chairman's verdict must answer, in order:

1. **Existence:** is the thing required — Yes / No / Conditional (state the
   condition)? One sentence, no hedging.
2. **Scope:** only if existence is Yes/Conditional, what exactly is in scope and
   what is explicitly out.
3. **Smallest decisive experiment:** the cheapest test that could falsify the
   existence answer, with what result would kill it.

Advisors must also answer existence before scope.

### 15.3 Kill criterion and cost of being wrong

Every advisor answer ends with two labelled lines, and the chairman must
consolidate them:

```
KILL CRITERION: <the evidence that would make this not worth building>
COST OF THE WRONG CHOICE: <time in weeks, and what is wasted, if the answer is wrong>
```

### 15.4 Deliverable and defensibility lens

When the decision is academic, a final-year project, a thesis, or a published
package, add a mandatory section to every advisor answer and to the verdict:

```
DELIVERABLE & DEFENSIBILITY: what artifact gets graded, demoed or published;
can it be finished inside the stated term; does it yield one coherent public
package, or does it split the story into two?
```

### 15.5 Build / keep / kill coverage checklist

Append to every advisor's prompt (analogous to 6.3; do not skip an area
silently — write "no view" if you have none):

```
This is a build / keep / kill decision. Beyond your style, cover each area.
Areas: existence and necessity (what actually breaks if this is never built);
scope and boundary (what it does, what it deliberately refuses to do); claim
viability (can the headline claim be measured, and is it falsifiable, or is it
unfalsifiable as instrumented); competitive landscape (who already ships this,
with verified sources); final-year defensibility (gradable, demoable, fits the
term); package coherence (one public artifact or two); effort to a
demonstrable version; and what is missing from the materials entirely.
```

### 15.6 Anti-contamination guards (from two documented incidents)

These exist because they really happened (see the run record):

1. **Reviewer fingerprint.** Before ranking, each reviewer must echo one line per
   anonymous response naming that response's actual recommendation. A review
   whose fingerprints do not match the real answers is discarded and re-run.
2. **Answer-file preflight.** Each reviewer `ls`-verifies that all five answer
   files exist and are non-empty before ranking. Reviews that saw fewer than five
   answers are void, not counted.
3. **Advisor file verification + verbatim recovery.** Immediately after the
   advisor batch, the orchestrator verifies each advisor file exists and is
   non-empty. If a subagent reported completion but wrote nothing, recover its
   output verbatim from the session store if possible, record the incident, and
   only then continue. Never write a role's output yourself (rule 4).
4. **Confabulation disclosure.** If any stage's output describes materials,
   files or answers that do not exist, record it in `verification.md`, show it,
   and re-run that stage. If for any reason its vote is kept, the orchestrator
   must state whether the outcome changes when that vote is dropped.

### 15.7 Competitor-claims table in the verdict

The chairman includes one small table:

```
Claim | Who makes it | Independently verified? | Source
```

and does not repeat any row as fact unless the "Independently verified?" cell is
Yes with a source from this run.

## 17. Add-ons for repo / service audit runs

Use these when the project review is of a repository or a running service as a
publishable artifact ("is everything working, is anything broken, is it good to
go, what is not needed, what is missing"). They add to sections 1–14 and may be
combined with section 15.

### 17.1 Verdict-per-item discipline

Every finding, in both the advisor answers and the chairman's register, carries:

```
DISPOSITION: Keep as-is | Fix in place | Rewrite | Remove | Missing (add)
SEVERITY: Critical | High | Medium | Low
EVIDENCE: <file:line, command output, or "unverified">
DONE WHEN: <the check that proves the fix>
```

A finding without an evidence pointer is `[OPINION]` and must say so. "Broken"
and "not needed" are two different findings; do not merge them.

### 17.2 Executed verification, not inspection

Advisors must actually run the artifact where it is safe to do so: the test
suite, the linter, the package build, an install into a throwaway environment,
the offline demo path, the CLI's own `--help` and diagnostic commands. Report the
exact command and its output. Reading code is necessary but not sufficient; a
claim about behaviour that could have been executed and was not is marked
`[UNEXECUTED]`.

### 17.3 Repo neatness and publish-readiness checklist

Append to every advisor's prompt (write "no view" rather than skipping an area):

```
Areas: repo inventory and dead/superseded files (name each, with evidence it is
unused); duplicated or competing sources of truth; doc staleness versus code;
packaging correctness (what ships, what must not ship, version, metadata,
entry points); install-and-first-run experience from a clean environment;
test coverage gaps and tests that assert nothing; code quality and structure
(module size, naming, dead code, error handling, typing); security and privacy
(credential handling, what is logged or stored, fail-open or fail-closed
behaviour); CI and release automation; licensing and legal (LICENSE, third-party
attribution, claim wording); the open-issue register carried from prior runs; and
anything missing from the materials entirely.
```

### 17.4 "Missing" is a first-class answer

The user explicitly asks "what is missing and what is not missing". The verdict
must contain two explicit lists: **MISSING (must be added before publication)**
and **NOT MISSING (verified present and adequate)**. Silence is not evidence of
completeness; every area in 17.3 either appears in one list or is marked "no
view".

### 17.5 The audit verdict shape

The chairman's verdict answers, in order:

1. **Is it good to go?** Yes / No / Yes-if (state the conditions). One sentence.
2. **What is broken** (correctness), **what is wrong** (honesty/staleness),
   **what is unnecessary** (removal), **what is missing** (addition) — four
   lists, each item carrying a disposition.
3. **The publication gate:** the smallest ordered set of actions that must be
   true before the artifact may be published.

## 19. Add-ons for exhaustive whole-repo verification runs

Use these when the user asks for a *deep, item-by-item* verification of a whole
repository or folder as it approaches publication — "go through every single
thing", "is everything working, is anything broken", "what is needed and what is
not", "code quality in detail", "give me the final wording of what is missing and
what is not missing so I can test it further". They add to sections 1–17 and
never replace the non-negotiable rules in section 3. Use §17 as the base and
this section as the sharpening; when they overlap, this section wins.

### 19.1 Plan before running (the user asked you to "step back")

Before framing, write `plan.md` into the run directory and send it to the user.
It contains, and nothing else:

```
## Scope
<the exact folder/repo, and what is explicitly out of scope, with the reason>

## The areas this run will cover
<the enumeration from 19.5, as a numbered list>

## What "verified" will mean here
<the executed checks: gate, build, install, every CLI command, every route, demo>

## Known from prior runs
<what earlier councils/runs already decided or fixed, so this run deltas and does
not re-litigate settled items — cite the run id and file>

## Cost estimate
<calls and rough input size, per section 10>
```

The plan is neutral: it lists areas and checks, never conclusions. It may quote
the user's request verbatim. Proceed after showing it unless the user objects.

### 19.2 The execution ledger (behaviour is executed, not inferred)

Build `execution-ledger.md`. Every entry is one row and one real command with its
real result; a claim about behaviour that was not executed is `[UNEXECUTED]`.

Enumerate and run, where safe in a disposable copy or venv:

1. **The gate:** test suite, linter, and any type-check the project configures.
2. **The build:** sdist and wheel; then `tar tzf` / `unzip -l` and assert the
   contents against the project's own claims (what ships, what must not ship).
3. **The install:** the built wheel into a throwaway venv, from a directory that
   is *not* the repo; run the installed console entry point.
4. **Every CLI command and every documented flag:** `--help` at each level, then a
   real invocation, including the diagnostic/doctor command and its exit codes.
5. **Every HTTP route the project claims to serve:** hit each one against the
   local process with the project's own mock upstream, and record status, headers
   and whether the documented rewrite did or did not happen.
6. **The documented demo/offline path:** run it end to end.
7. **Failure paths:** at least the documented error cases — missing config,
   refused wider bind, oversized body, unknown model, upstream error.

Rows are `CHECK | COMMAND | RESULT | PASS/FAIL/UNEXECUTED`. A FAIL is a finding;
so is a documented behaviour that no command exists to demonstrate.

### 19.3 The removal bar (prove dead, or it stays)

For every file the run proposes to remove, the item is not "Remove" until it
clears all three, each recorded with its command output:

1. **No reference:** `grep -rn` over the whole repo (excluding the file itself)
   for its name and its stem finds nothing that is not itself historical.
2. **Not loaded by the build or tests:** the gate and the build both pass with it
   gone, in a scratch copy.
3. **Not documented evidence:** no live doc, README, runbook or the SSOT reads it
   back as evidence.

If any of the three fails, the disposition is **Keep**, and the finding records
*why* it was considered and retained. "It looks unused" is never the bar. This
exists because the obvious dead-file list is usually wrong: of eleven files an
earlier run named for removal, exactly one was actually dead and the rest were
load-bearing for tests or docs.

### 19.4 Code-quality rubric (per module, with numbers)

Code quality is a first-class area, not a checklist line. For every non-trivial
module report, with the number that supports it:

```
SIZE: lines, and the largest function/class in it
STRUCTURE: one clear responsibility, or several mixed (name them)
TYPING: annotations present and meaningful, or absent/partial
NAMING: consistent with the project's own conventions
DEAD CODE: unreachable branches, unused imports/params, commented-out blocks
ERROR HANDLING: fail-open or fail-closed on each path, and whether it is
  consistent with the project's stated posture
COUPLING: imports and side effects at import time
TEST SEAM: is the unit testable without network/disk, and is it tested
```

An oversized module (rule of thumb: over ~800 lines, or a single function over
~80) is a finding with the specific split named, not a vague "could be cleaner".
A module that is large but cohesive and well-tested is reported as sized but
adequate — do not inflate a style preference into a defect.

### 19.5 Coverage-completeness attestation (nothing may be skipped silently)

The chairman's verdict ends with an attestation table mapping **every** area
below to where it landed: one of the two lists in 19.6, or an explicit
"no view — reason". An area that appears nowhere is itself a defect of the run.

```
A. Repo inventory: every tracked file classified (keep / remove / move)
B. Dead, duplicated or superseded artifacts
C. Sources of truth: one, or several competing
D. Docs vs code: every factual doc claim that could be stale
E. Packaging: what ships, metadata, version, entry points, the build contents
F. Install and first-run from a clean environment
G. Code quality (per 19.4), module by module
H. Tests: coverage gaps, tests that assert nothing, fixture-only claims
I. Security and privacy: credentials, what is stored/logged, fail-open/closed
J. CI and release automation, and the publish path
K. Licensing and legal: LICENSE, attribution, claim wording, privacy
L. Claims honesty: every public claim versus what is provable
M. Behavioural verification (per 19.2): the full surface executed
N. Operations and reliability: failure modes, limits, recovery
O. Product and first-use experience for a stranger
P. Research/evidence validity: what is measured, sample size, what is not
Q. Commercial and distribution: buyer, competitors, go-to-market
R. Carried-open items from every prior run, each resolved or explicitly carried
S. What is missing from the materials entirely
```

### 19.6 The two-list deliverable, in a form an agent can execute

The user wants the **final wording** they can paste into any agent and act on.
So each list is not prose; each item is a self-contained, ordered task:

```
[N] <one-line title>
    DISPOSITION: Add | Fix in place | Rewrite | Remove
    SEVERITY: Critical | High | Medium | Low
    WHY: <the evidence, file:line or command output>
    DO THIS: <the exact change, specific enough to be done without re-reading this run>
    VERIFY: <the exact command whose output proves it is done>
    BLOCKED BY: <owner action or prior item, or "nothing">
```

**MISSING** lists only items that must be added or fixed before publication.
**NOT MISSING** lists areas verified present and adequate, each with the evidence
that makes it adequate — so a reader can trust the negative. Do not pad either
list; a short true list beats a long padded one.

### 19.7 What the user may have missed (the run's own contribution)

End the verdict with a short section, **"What the request did not ask for, but
should be decided"** — the items the user's own framing omitted, each with why it
matters now and the cost of ignoring it. The user explicitly asked for this. Keep
it short and concrete; do not use it as a second finding dump. Typical shape:
a decision that belongs to the owner (money, naming, legal), a downstream
consequence of a choice already made, and a risk that only appears after
publication.

## 18. Change log

### v1.3 (2026-10-20)
- Added section 19: exhaustive whole-repo verification add-ons — a written plan
  before framing (19.1), the executed-verification ledger across the whole surface
  including every CLI command and HTTP route (19.2), the three-part removal bar
  (19.3), a per-module code-quality rubric with numbers (19.4), a
  coverage-completeness attestation table so no area can be skipped silently
  (19.5), the two-list deliverable in agent-executable task form (19.6), and the
  "what the request did not ask for" section (19.7).
- Unchanged: sections 1–17.

### v1.2 (2026-10-20)
- Added section 17: repo/service-audit add-ons — verdict-per-item discipline
  (disposition, severity, evidence, done-when), executed verification rather than
  inspection (`[UNEXECUTED]`), the repo neatness / publish-readiness checklist,
  "missing" as a first-class two-list answer, and the audit verdict shape.
- Renumbered the change log to section 18.

### v1.1 (2026-10-19)
- Added section 15: claim grading with `[VENDOR-CLAIM]`; two-part verdict
  (existence then scope); kill criterion and cost-of-wrong-choice lines;
  deliverable-and-defensibility lens; build/keep/kill coverage checklist;
  anti-contamination guards (reviewer fingerprint, answer-file preflight,
  advisor file verification with verbatim session-store recovery, confabulation
  disclosure); competitor-claims table.
- Added this change log.
- Unchanged: sections 1–14, including all non-negotiable rules and prompts.

### v1.0
- Original skill (sections 1–14).
