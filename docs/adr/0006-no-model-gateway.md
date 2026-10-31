# Do not bundle a model gateway; keep model switching manual

Status: accepted

The add-on runs one T3 Code server with OpenCode as its harness, and OpenCode
talks to the model providers directly. A user asked to add CLIProxyAPI to the
container so that requests would use the free OpenCode models first and fall
back to paid DeepSeek credits once those free models were exhausted. Read
literally, that is a routing problem: one endpoint, two upstreams, a preference
order and automatic failover. It is not solvable with a gateway here, for three
independent reasons.

The free models are not reachable from a proxy. OpenCode Zen's free tier is
served to the OpenCode client only ("free-tier chat models require OpenCode; use
paid models or Go from other clients"), and its limits apply **per IP
address**: signing in or adding credits does not raise them. A gateway living
in the container would be the HTTP client, so it would collect 429s, not
quotas.

CLIProxyAPI, like the comparable gateways, resolves credentials rather than
models. It picks among several credentials for the model the client already
requested (`round-robin`, `weighted-round-robin`, `fill-first`, `priority`,
cooldown on 429). Nothing in its configuration expresses "try model A, then
model B"; the only hook for that is a trusted in-process Go plugin, which is
disabled by default.

OpenCode has no fallback chain either. Its configuration exposes `model`,
`small_model`, `agent.*.model` and `command.*.model`, and the session runner
resolves exactly one of them: when the pinned model is unavailable it raises
`ModelUnavailableError` instead of switching. Runtime failover is an open
feature request upstream.

We therefore add no gateway to the image and automate no switch. Model choice
stays manual: new threads start on a free zero-retention model, and the user
picks a paid model from the T3 Code selector when a free one is rate-limited.
That recommendation lives in `DOCS.md`; there is no option, no second port and
no supervised process.

## Considered Options

- **CLIProxyAPI in the image**: rejected on facts. It cannot reach the free tier
  at all, because the quota belongs to the OpenCode client and is counted per
  IP, and with a single paid DeepSeek account its credential pooling has nothing
  to pool. It would add a supervised Go process, a configuration surface, an
  auth directory and a management port for no change in behaviour.
- **A community fallback plugin** (`opencode-rate-limit-fallback`,
  `opencode-auto-fallback`, and similar): these abort a rate-limited turn and
  resend the last user message on the next model. They work, but they replay a
  whole conversation on the paid model, they run third-party code in-process
  with the user's credentials, and their interaction with T3 Code's thread state
  is untested. Rejected as a default; the user explicitly chose to keep control.
- **A home-grown plugin**: the same effect with less trust surface, but a new
  component to maintain against an unstable plugin API, for a saving of a few
  cents per session.
- **Waiting for native failover**: OpenCode has the request open upstream.
  Revisit when it ships; this ADR then becomes obsolete rather than wrong.
- **Per-agent model configuration**: not a fallback, but agents such as the
  title or explore helpers can already run on a free model through
  `opencode_config_json`, which captures part of the intent at no cost.

## Consequences

- A rate-limited free model fails the turn. The user switches models in the T3
  Code selector; nothing recovers automatically.
- The image, its options, its single port and its release metadata are
  unchanged.
- `DOCS.md` recommends `opencode/deepseek-v4.1-flash-free` as the default for
  new threads, both because it is free and because it follows a zero-retention
  data policy, unlike several other free models that may train on prompts. Free
  models are advertised "for a limited time" and rotate, so that documented
  default can rot, and no automated check covers it.
- There is no usage or cost dashboard, no multi-account pooling and no unified
  `/v1/models` endpoint; those needs stay unaddressed by design.
