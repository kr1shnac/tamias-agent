# Advisor: first_principles — Answer B

## What is actually being solved

Not "which layer to add." The unasked question is **against whom is the fence drawn?** The option list (A/B/C) presumes the fence is drawn against the *model* while the *local user* is inside it. If the fence is meant to bind the employee, options A and B both fail by construction and C fails without client-side pinning.

## Hidden assumptions, challenged

1. **"The policy is an authority."** It is a TOML file read by the same process the user controls. [FACT] `policy_check` returns `None` outright when `_ACTIVE_POLICY is None` (`agent.py:2786-2788`), so a run without `--policy`/`--company-id` has **no** tool, path, shell, or domain gate at all. Bypass #1 is "don't opt in." [FACT]
2. **"Managed mode is a company guarantee."** [FACT] the agent does not verify the manifest signature (`docs/BOUNDED-AGENT.md:146-149`); `docs/RELEASE-STATUS.md:41` already concedes "Bring your own gateway bypass possible." A user points `TAMIAS_BASE_URL` at any host serving any policy. [INFERENCE, High]
3. **"deny_read is per-file."** It is per-*argument*. [FACT] only `trace_feature` re-checks each file (`agent.py:1769-1771`); `search_in_files` (`:1550-1554`), `investigate_target` (`:1694`), `list_directory` (`:1404`), `analyze_structure` check only the secret name denylist. So `search_in_files("token", "company/work/todoinc")` reads `chatbot/*.py` and `hr/*.md` — the exact probe #4 the team believes passes. The demo passes because the probe uses the *denied path as the argument* (`demo/check_boundary.py:87-88`). [FACT code / INFERENCE exploit, High]
4. **"Shell families are scoped."** Deny is substring (`agent.py:2804`), allow is substring (`:2807`), executed with `shell=True` (`:1251-1253`). `python3 -m pytest` is an allowed family and pytest executes `conftest.py` — arbitrary Python with no token scan. `python3 -m pytest >/tmp/x` also passes `shell_escapes_company` because the token starts with `>`, not `/` (`:1193`). [INFERENCE, High; unverified by execution]
5. **"The boundary is the product."** It is the company. `resolve_in_company_workspace` fences at `company/work/<id>/` (`:1486`); the product fence is `allow_write` only. [FACT] For `todoinc`, reads of any other app are legal.

## Threat model (my read)

Trusted: the gateway (only in managed mode, and only by assertion), the local Python process, the OS. Untrusted: the remote model. **The local user is treated as trusted, which is the whole problem.** [OPINION, High]

## Scope

Company ≠ product ≠ task. Company and product diverge on reads (above). Task diverges furthest: `domain_check` is lexical and self-declared "not a security boundary" (`agent.py:2873-2875`); the plan gate holds shell to a signature but not to the file list (framed §4). The task boundary is prose. [FACT]

## Evidence

374 tests prove the dispatcher behaves as written for the *probed argument forms*. They do not prove escape resistance; no test I saw asserts the parent-directory or redirect paths. `demo/check_boundary.py` "denied-below" accepts *any* `Error:` (`:115-118`) — a weak assertion. [FACT]

**Demo-blocking:** none of the above. **Production-blocking:** (1) opt-out by omission, (2) per-file deny_read, (3) shell `shell=True`, (4) unpinned gateway.

The question optimizes the wrong variable (layer count) instead of the trust set. **Option D**: declare the fence anti-model only, then B is proportionate; declare it anti-employee and you need C with client-pinned keys *plus* B — A is not an option in that world at all.

**One-day step:** add `demo/attacks.py` — 8 probes expected to *succeed* today (search from parent, list from parent, `>/tmp`, conftest pytest, no-policy run, rogue gateway), each xfail-documented in RELEASE-STATUS. Convert the claim from "boundary holds" to a calibrated table in one day.

One-line verdict: The fence is real against the model and fiction against the user — publish the trust set before adding layers.
