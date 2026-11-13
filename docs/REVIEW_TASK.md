# Caller controls for a delegated review

The caller can tailor the work through `TASK_FILE`. Copy
[the task template](../templates/review-task.yaml), fill it with the real objective
and input locators, and pass its path to the
[delegation recipe](PACKET_DELEGATION.md). The recipe retains the assignment as
`task.md` beside the packet and sends that same snapshot to the receiver.

These settings are instructions interpreted by the receiving agent. The launcher
passes the task text through; it does not parse or validate a configuration file.
Existing plain-text assignments remain usable. Resolve their scope and controls
into the same review-log record before substantial work.

## Controls and defaults

| Control | Caller choice | Default or requirement |
| --- | --- | --- |
| `objective` | The question or decision this review should inform | Required |
| `questions` | Questions in priority order, answered individually | Empty list |
| `scope.mode` | `targeted`, `full`, or `delta` | `targeted` |
| `scope.contracts` | Exact paths relative to `BASELINE_DIR`; `all` is allowed in full mode | Explicit list required for targeted and delta; `all` for full |
| `scope.source_locators` | Files and sections relative to `REVIEW_SOURCE` that bound source inspection | Required list of locators, or `all` for all supplied source material |
| `scope.previous_review` | Retained prior packet relative to `REVIEW_SOURCE` | Required for delta |
| `scope.change_context` | Supplied changes and affected claim paths for a delta review | Required and nonempty for delta |
| `focus` | Any subset of `wording`, `denominator`, and `coverage` | All three |
| `proposal_mode` | `findings_only` or `suggest` | `suggest` |
| `missing_inputs` | `continue_available` or `return_blocked` | `continue_available` |
| `effort.minutes_target`, `effort.tokens_target` | Positive planning targets, or null | Null; no implied target |
| `output.detail` | `concise` or `detailed` explanations | `concise` |
| `output.max_summary_findings` | Positive limit on highlighted findings | 5 |

The template chooses a targeted denominator/wording review and findings-only
output to illustrate a narrow assignment. Its paths and questions are synthetic.
Replace them before launch.

Resolve selected contract paths against the retained baseline and preserve that
relative layout in `contracts/`. Record the exact selected inventory in the
review log. An empty or unresolved selection blocks the review. Contracts outside
an explicit subset are out of scope, and are excluded from the returned-inventory
comparison. Report them as unreviewed rather than silently including them.

For full mode, use `scope.contracts: all` and inspect the entire caller-retained
inventory. Use targeted mode for an explicit subset. The source scope still applies.
For delta mode, inspect the selected changed claims and caller-identified affected
claims. Read the supplied previous review and change context, record what was
rechecked, and retain unresolved earlier findings relevant to those claims.
If prior artifacts cannot be read, return blocked instead of claiming a delta
review. A previously successful report still needs its binding checked before
reuse, and current selected contracts still undergo deterministic validation.

## Receiver behavior

The caller retains its own version of the assignment for the completion check.
Record the effective assignment in `review-log.md` before substantial work.
Resolve omitted optional fields using the table above and record those defaults.
Ask for clarification or return blocked when required scope is missing, a value
is unknown, or instructions conflict. Never silently reinterpret an unfamiliar
control. The caller's explicit scope and priorities take precedence over the
suggested two-or-three-claim pilot and the default inspection menu.

Perform the selected focus checks and answer the prioritized questions within the
supplied source scope. An empty focus list requests only the mechanical checks
and any inspections specified in questions. Questions can request additional
specific inspections, such
as tracing a named calculation. Record those alongside the named focus checks.
When a question requires evidence outside scope, identify the needed input and
apply the missing-input policy.

In `findings_only` mode, return observations, supporting locators, and unresolved
questions. In `suggest` mode, also write useful candidate revisions in `proposed/`
with the existing diff, reason, source, and pending-decision record. Neither mode
authorizes adopting revisions.

With `continue_available`, finish the checks supported by available inputs and
mark dependent checks blocked. With `return_blocked`, stop substantive review
when an input needed for an assigned check is missing, preserve completed work,
and return the exact missing input and the question it prevents answering.

Track effort against the requested targets using actual available telemetry.
At a target boundary, save a resumable partial result with completed work,
remaining questions, and the next bounded step. Token usage is unknown when the
runtime does not expose it. A caller that needs a hard timeout or token cap must
enforce it in its execution environment. These prompt settings provide planning
guidance.

## Return useful answers

The packet should lead with the objective and answers to the caller's prioritized
questions. For each answer, cite its source or executed check, state remaining
uncertainty, and identify the concrete follow-up input or action when requested.

Retain a work table in `review-log.md` with the selected contract, requested check,
status (`completed`, `blocked`, or `not_requested`), supporting artifact, and any
remaining work. Completion of an inspection describes work performed and can
include a discovered error. It is separate from the validator's verdict.
Checks deferred by the effort target are blocked with that reason.

Return the packet path, overall work status (`complete`, `partial`, or `blocked`),
answers, artifact paths, actual check exit codes, and a focused next step.
Use complete only when all assigned checks and required mechanical checks finish.
Use partial when useful assigned work finished but some remains, and blocked
when the assigned review could not proceed. Report work status in the narrative
and log; it does not replace READY / REVIEW / BLOCK.

A concise packet can highlight the requested number of findings while retaining
all findings in its linked artifacts. The summary limit never drops validator
findings, unresolved assigned questions, or proposal changes from the record.

## Required boundaries

Caller controls select the work and presentation. Every selected contract still
needs a retained baseline, drift comparison, deterministic validation, and
preserved raw reports. Caller completion checks still verify report bindings and
packet links. Baseline integrity failures stop acceptance. Preserve unknowns,
scope notices, explicit proposal acceptance, and the actual source/tool revisions.

A passed link check alone does not establish that the assigned work completed.
Report checks outside the requested focus as not requested.
