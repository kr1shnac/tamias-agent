## Decision

Review the boundary model in this repository and decide what should change, if anything, before the boundary is presented as a company guarantee. Assess whether a boundary set by a company can be bypassed or exceeded, and whether enforcement is proportionate and limited to the assigned task.

## Options

- **A. Keep the in-process dispatcher as the authority.** Close concrete gaps inside the current policy/company/product/tool/path/ask model; do not add a new isolation layer.
- **B. Keep the dispatcher as the policy layer, and add mandatory OS/container isolation plus network egress control below it.** The local process is treated as fallible; the kernel/container becomes the hard boundary.
- **C. Move authority to a trusted gateway with a client-pinned signed manifest, and treat the local agent as an untrusted UI.** Combine this with B where the work actually executes.
- **D. Something else / none of these.**

## Constraints and context given by the user

> "This boundary issue has been the part of this project for a very long time."

> "making sure that this boundary should not be bypassed if the company sets the boundary. The boundary should be concisely upheld to that particular task. It should not exceed."

> "people should not be able to bypass that."

The repository's own rule: live claims need two consecutive passes; offline and mock runs must be labelled; do not commit or push without explicit instruction.

## Materials

Read these files in the repository. Paths are relative to `/home/krish/Desktop/tamias-agent`. The excerpts below are verbatim where quoted; the files are authoritative.

### 1. The policy under review — `policies/todoinc-todo.toml`

```toml
version = "1"

[use_case]
name      = "todo-app"
root      = "company/work/todoinc/apps/todo"
company   = "todoinc"
read_only = false

[domain]
allow = ["todo", "to-do", "to do", "task", "task list", "checklist", "item", "due date"]
deny  = ["chatgpt", "chat gpt", "chatbot", "chat bot", "llm", "gpt", "openai",
         "build an agent", "crypto", "trading bot", "rag", "clone", "linkedin",
         "facebook", "instagram", "netflix", "uber", "amazon", "twitter"]

[tools]
allow = ["read_file", "search_in_files", "list_directory", "create_directory", "edit_file", "write_file", "run_shell", "update_plan", "investigate_target", "trace_feature", "analyze_structure", "build_similar", "record_unknown", "record_comparison", "finish_investigation", "boundary_accuracy", "model_performance_comparison", "reasoning_chain"]
ask   = ["write_file", "edit_file", "create_directory"]

[run_shell]
allow   = ["python3 -m pytest", "git status", "git diff", "git log"]
deny    = ["rm ", "mv ", "curl ", "wget ", "git push", "chmod ", "cat ", "ssh "]
timeout = 30

[paths]
allow_write = ["company/work/todoinc/apps/todo/**"]
deny_read   = [
  "company/work/todoinc/apps/chatbot",
  "company/work/todoinc/apps/chatbot/**",
  "company/work/todoinc/hr",
  "company/work/todoinc/hr/**",
  "**/*.pem",
]

[audit]
path = "policies/todoinc-todo.audit.jsonl"
```

### 2. The probes the team uses — `demo/check_boundary.py`

The file wires the company fence (`company/work/acme/`) and the product fence (`bots/codefix/`) and asserts:

| Probe | Expected |
|---|---|
| read/list/search/run tests inside the product | ran |
| read/search/write another project in the same company | deny |
| read `hr/salaries.csv` | deny |
| write into the product headless | ask-denied |
| shell `rm`, `curl`, `ls -la` | deny |
| read the policy file, `.env`, or a repo file outside the company | refused below the policy |
| the same write after a human says yes | ran |

### 3. The to-do probes — `demo/showcase.py`

`DOMAIN_PROBES` includes allowed requests (`build a todo app`, `sort by due date`, `refactor the task list`) and refused requests (`chatbot`, `clone linkedin`, `weather`, `hi`). `TOOL_PROBES` includes product read (allow), product write (ask), chatbot write (block), HR read (block), private key read (block), product tests (allow), `rm -rf company` (block), `git push` (block), `fetch_url` (block). The exact lists are in `demo/showcase.py`.

### 4. Enforcement code — `agent.py`

The relevant functions are:

- `resolve_in_workspace(path)` and `resolve_in_company_workspace(path, company_id)` — realpath containment, with the company id checked as a single path segment.
- `shell_escapes_company(command, company_workspace)` — token scan for `~`, `..`, and absolute paths outside the company.
- `run_shell(command)` — `subprocess.run(..., shell=True, cwd=company_workspace, env=scrubbed_env())`, with the company and secret checks before execution.
- `policy_check(tool_name, args)` — tool allow/deny, read-only, shell command-family substring allow/deny, `allow_write` / `deny_read` globs, and the `.` project-root hint.
- `policy_ask(tool_name, args)` and `_policy_gate(...)` — ask-gated tools, deny wins, audit rows.
- `dispatch_tool(tool_name, args)` — plan gate, dossier gate, policy gate, ask, checkpoint, then the tool.
- `domain_check(text)` — lexical allow/deny gate over the request text before a model call.
- `policy_audit(...)` — in-memory rows plus optional JSONL append.
- `protect_path` / `is_sensitive_path` / `refuse_secret` — `.env`, key files, and the local policy path.
- `fetch_policy` / `enter_managed_mode` — `GET /policy` from the gateway; refuses direct provider URL and non-gateway token; parses the served policy; does not verify a signature in the agent.
- `plan_write_block` — signed plan, file-list drift for writes; shell is in `PLAN_GATED_TOOLS` but is not path-scoped by the signed file list.
- `dossier_write_block` — first mutating call held until an investigation tool returns evidence.

### 5. The design's own statement — `docs/BOUNDED-AGENT.md`

Sections 3–4 and "Honest limits" state the intended layers: tool allowlist → filesystem scope → network scope → secret control → shell sandbox → audit log. The same document says: "`run_shell` is the sharp edge: without an OS sandbox ... a determined prompt-injected command can still find unguarded operators." It also says the gateway verifies the manifest signature, and "the agent does not itself check the signature — that is the gateway's job."

### 6. Current release state — `docs/RELEASE-STATUS.md`

The "What is blocked" table currently lists: live model path (latest 0/2, rate-limited), live benchmark, MCP boundary server (not built), OS sandbox (not built; "best-effort shell guard only"), and client-pinned manifest (not built; "'Bring your own gateway' bypass possible"). The full suite is 374 passing tests; the offline gate is 13 passed, 0 failed, 1 skipped.

### 7. The boundary queries the team is focusing on

These are the current acceptance probes. They are evidence of intent, not a claim that every probe is sufficient.

1. **Topic / use case:** in-scope `todo`/`task` requests reach the model; off-topic (`chatbot`, `crypto`, `clone linkedin`, `weather`, `hi`) are refused before spend; deny wins over allow.
2. **Company:** `company/work/todoinc/**` is reachable; another company id, a traversal id, or a path outside the company is refused.
3. **Product:** writes are only `company/work/todoinc/apps/todo/**`; another app, `hr/`, `*.pem`, `.env`, the policy file, and repo-root paths are refused.
4. **Read denial:** `hr/`, `chatbot/`, `*.pem` are not read, listed, searched, or returned by investigation tools.
5. **Tools:** only the allowlist runs; hard deny wins; read-only blocks every write and shell.
6. **Ask:** `write_file`, `edit_file`, `create_directory` are ask-gated; TUI **Y** runs, **N** refuses; headless refuses fail-closed; deny wins over ask.
7. **Shell:** only the named command families run; `rm`, `mv`, `curl`, `wget`, `git push`, `chmod`, `cat`, `ssh`, absolute paths outside the company, `..`, and `~` are refused; cwd is the company area; the environment is scrubbed; timeout is 30s.
8. **Paths:** absolute, relative, `..`, `~`, symlink, and `.` are resolved with realpath; a symlink pointing outside is refused.
9. **Plan / dossier:** writes outside the signed file list stop the turn; a mutating call before evidence is held; shell is signature-gated but not path-scoped.
10. **Managed policy:** `--require-proxy` refuses a direct provider URL, a provider key, or no policy; the gateway serves the policy; local policy and managed policy cannot be combined.
11. **Audit:** every gate decision is recorded (allow/deny/ask-allowed/ask-denied), bodies are redacted, and JSONL is appended when configured.
12. **Secrets:** `.env`, key files, and the policy file are never read, written, searched, or printed by the tools; the shell environment is scrubbed.

### 8. The trust questions the team wants checked

- Who is trusted: the remote model, the local user, the local Python process, the company gateway, the OS?
- Is the fence per action and fail-closed, or can one tool/shell/investigation path exceed it?
- Is the boundary the company, the product, or the task? Where do those three diverge?
- Can a model that is allowed to run tests or shell commands use that capability to mutate another project, read a denied path, reach the network, or rewrite the policy/audit?
- What is the real guarantee when the policy is a local TOML file, when managed mode trusts the gateway response, and when the agent itself can be modified by the local user?
- Which gaps are demo-blocking, which are production-blocking, and which are honest limitations that should be stated rather than "fixed" by prose?
- What evidence would prove the boundary holds, beyond the current 374-test suite and 17-probe demo?

## Current facts

No web search was used. The repository is the source of truth for this review.
