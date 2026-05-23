# driftwatch

> Agent that polls cloud resource configs and alerts when they drift from a defined baseline.

---

## Installation

```bash
pip install driftwatch
```

Or install from source:

```bash
git clone https://github.com/yourorg/driftwatch.git && cd driftwatch && pip install -e .
```

---

## Usage

Define a baseline config file (`baseline.yaml`):

```yaml
resources:
  - id: sg-0abc123
    type: security_group
    expected:
      ingress_ports: [443, 80]
  - id: s3-my-bucket
    type: s3_bucket
    expected:
      public_access_blocked: true
```

Run the agent:

```bash
driftwatch run --baseline baseline.yaml --interval 60
```

Driftwatch will poll your cloud resources every 60 seconds and alert when any configuration no longer matches the defined baseline.

**Example alert output:**

```
[DRIFT DETECTED] s3-my-bucket | public_access_blocked: expected=true, actual=false
```

Alerts can be routed to Slack, PagerDuty, or stdout via the `--alert` flag:

```bash
driftwatch run --baseline baseline.yaml --alert slack
```

---

## Configuration

| Flag | Description | Default |
|------|-------------|---------|
| `--baseline` | Path to baseline YAML file | `baseline.yaml` |
| `--interval` | Poll interval in seconds | `300` |
| `--alert` | Alert destination (`stdout`, `slack`, `pagerduty`) | `stdout` |
| `--once` | Run a single poll and exit instead of looping | `false` |

---

## Environment Variables

Sensitive configuration such as webhook URLs and API keys should be provided via environment variables rather than command-line flags:

| Variable | Description |
|----------|-------------|
| `SLACK_WEBHOOK_URL` | Incoming webhook URL for Slack alerts |
| `PAGERDUTY_ROUTING_KEY` | Routing key for PagerDuty Events API v2 |

---

## License

MIT © 2024 driftwatch contributors
