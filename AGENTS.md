

<!-- tpl:repo-followthrough:start -->

## Scoped Execution And Completion

Policy version: `repo-completion-v8-2026-09-24`.
Repository-specific security, data, integration, and promotion restrictions
remain authoritative within the task.

- Treat action requests as work to finish, not an acknowledgment of capability;
  honor planning-only requests. Keep accepted outcomes across side questions
  and checkpoints. An intermediate milestone, tests, or a review packet is not
  proof of a requested practical run; require observed acceptance evidence.
- Accepted-plan implementation includes reversible gate repair, preservation,
  and review publication without renewed questions. Native gates still apply.
- For a multi-step task or accepted plan, check the full outcome list before
  voluntary closeout. Use the installed deck's completion/handoff check when
  available; otherwise use the linked policy's manual checklist.
  Continue authorized work behind scoped blockers; investigate unknown inputs
  before asking the user.
- Before promising a live run, identify its exact approvals and their current
  evidence. Prepare the reviewable decision first. A plan does not itself grant
  live-action authority; preserve project security and promotion gates.
- If no authorized useful action remains, report the exact affected outcome,
  missing input or rule, attempted versus proposed alternatives, owner, next
  action, and completion proof. Do not invent approvals or retry uncertain
  mutations. Higher-priority instructions and native rules win over a skill.
- Reuse unchanged evidence. Add or repeat a check only for a native gate,
  changed behavior, or a named uncertainty; do not add generic stopping points.

<!-- tpl:quality-review-v1 -->

- For consequential changes, inspect assumptions and use independent outcome
  evidence plus one bounded false-pass check. Unknown review coverage is not
  success; project profiles are review candidates, not automatic gates.
- Start or resume in the owning project root and reread its effective policy
  after a policy change. Linked Markdown is not automatically loaded by Codex.
  Keep hooks retired; do not delegate unless I explicitly request it in the
  current prompt.

First policy/state route (from the project root):
`../../.templates/scripts/tpl context-primer --policy-refresh --repo-root .`.
Shared policy reference:
`../../.templates/docs/observability/task_completion_policy.md`.

<!-- tpl:repo-followthrough:end -->
