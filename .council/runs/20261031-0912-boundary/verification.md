# Verification of high-impact council claims

Checked on 2026-10-31 against this repository. Line numbers are approximate
because this file is evidence for a hand-off, not a substitute for reading the
code.

Full suite after the check: **374 passed in 16.74s**
(`.venv/bin/python -m pytest -q`). No live model call was made.

## 1. `deny_read` is per-argument, not per-file

**Status: CONFIRMED, with a correction to the council wording.**

Evidence in code:

- `policy_check` globs the `deny_read` list against the single path argument
  passed to the tool (`agent.py`, policy path section around `DENY READ`).
  It does not glob or filter the paths a directory tool later returns.
- `search_in_files` resolves only its `directory` argument, then walks the tree
  and skips only `is_sensitive_path(file_path)` per file.
- `analyze_structure` walks a directory and includes `.py`, `.js`, `.ts`
  files under it with no per-file `deny_read` check.

Offline check (policy `policies/todoinc-todo.toml`, `COMPANY_ID=todoinc`):

```text
policy_check(search_from_company_root): None
chatbot_py_returned: True
hr_csv_returned: False
analyze_from_company_root: None
analyze_lists_chatbot: True
```

Confirmed consequence: a call like `search_in_files("def ",
"company/work/todoinc")` or `analyze_structure("company/work/todoinc")`
passes the policy gate when the denied directory is nested rather than supplied
as the argument.

Correction: for the current sample tree, `search_in_files` did **not** return
`company/work/todoinc/hr/salaries.csv`, because `search_in_files` scans only
`.py`, `.txt`, `.md`, `.json`, `.js`, `.ts`, `.html`, `.css` and `salaries.csv`
is a `.csv`. It did return `apps/chatbot/src/bot.py`, which is in
`paths.deny_read`. So the council's read-bypass claim is confirmed; its
specific claim that `search_in_files` returns HR salary CSV content is
contradicted for this fixture.

## 2. Shell allow/deny is substring-based and `run_shell` is not ask-gated

**Status: CONFIRMED.**

Evidence:

- `policy_check` accepts a `run_shell` command if it contains any
  `[run_shell].allow` substring, and denies it if it contains any
  `[run_shell].deny` substring.
- `run_shell` executes `subprocess.run(command, shell=True, cwd=..., env=...)`.
- `policies/todoinc-todo.toml` puts only `write_file`, `edit_file`, and
  `create_directory` in `[tools] ask`; `run_shell` is absent.
- `shell_escapes_company` scans tokens for `~`, `..`, absolute paths and secret
  names. It does not reject shell operators after an allowed family.

Offline gate check (command not executed):

```text
policy_check(shell_composite): None
policy_ask(run_shell): None
policy_check(shell_log_other_app): None
```

Confirmed consequence: the policy layer currently passes
`python3 -m pytest -q; python3 -c ...` and
`git log -p apps/chatbot/src/bot.py` before execution. Whether the operating
system allows the later action to succeed is a separate, unbuilt layer.

## 3. Managed mode does not verify a signed manifest in the agent

**Status: CONFIRMED by code inspection.**

- `fetch_policy` performs `GET /policy`, parses JSON, and returns
  `payload["policy"]`.
- A grep of `agent.py` for `verify/signature/public_key/pin` in the policy-fetch
  path found no signature verification.
- `docs/RELEASE-STATUS.md` already records `Client-pinned manifest: not built`.

Consequence: managed mode is only as strong as the transport plus the gateway
trust boundary. Saying the manifest is verified by the gateway is honest; saying
the agent verifies it is not.

## 4. No active policy means no policy gate and no audit row

**Status: CONFIRMED.**

- `policy_check` returns `None` when `_ACTIVE_POLICY is None`.
- `policy_audit` returns immediately when `_ACTIVE_POLICY is None`.
- `resolve_in_company_workspace` degrades to the workspace fence when no
  company id is set.

Consequence: a run that omits or bypasses policy (for example `--unbounded`, or
a checkout whose deployment default policy path is absent) has no tool/path/
shell gate and is not recorded in the policy audit trail as “fence off.”

## 5. The plan contract is local human approval, not cryptographic signing

**Status: CONFIRMED.**

- `agent.py` records `contract_line = "contract: signed by user"` when a user
  approves a plan.
- No key material, signature, public-key pin, or off-host attestation was
  found in the plan-contract path.

Consequence: the plan contract can scope writes when the TUI is used, but it is
self-attested in the same local trust domain. Do not describe it as externally
signed.

## 6. The `fetch_url` demo probe does not prove egress control

**Status: CONFIRMED.**

- `demo/showcase.py` contains a `fetch_url` probe.
- `fetch_url` is not in `policies/todoinc-todo.toml` `[tools].allow`, so the
  probe shows an unknown/disallowed tool is rejected.
- It does not show that a shell network command is blocked.

Consequence: describe that probe as “unknown tool rejected,” not as “network
egress blocked.”

## 7. Test counts and claims

**Status: CONFIRMED for this run only.**

- `.venv/bin/python -m pytest -q`: **374 passed in 16.74s**.
- No live model run was executed for this council/report, so no live-pass claim
  is made.
- The adversarial composition probes above were code inspection and a
  read-only/offline Python helper, not `demo/check_all.sh`.

## Final correction applied to the council verdict

The council's central conclusion stands: the in-process fence is real per
action for canonical probes, but it is not a company guarantee and can be
exceeded. The wording must be narrowed:

- Confirmed: nested denied reads and company-wide shell are real gaps.
- Corrected: `search_in_files` did not return `.csv` HR content in the sample
  tree; the commission was denial of nested non-CSV sensitive files, notably
  `chatbot/src/bot.py`, and path listing in analysis.
- Unverified by execution: the exact network/execution effect of the permitted
  composite shell commands. Running them was deliberately not part of this
  verification.
