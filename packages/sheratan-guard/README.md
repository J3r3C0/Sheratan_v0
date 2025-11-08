# Sheratan Guard

Policy engine, PII detection, and audit logging for security and compliance.

## Features

### Policy Engine
- Configurable policy rules
- Actions: ALLOW, DENY, REDACT, WARN
- Custom condition evaluation

### PII Detection
- Detects common PII types:
  - Email addresses
  - Phone numbers
  - Social Security Numbers
  - Credit card numbers
  - IP addresses
- Automatic redaction
- Detailed scanning reports

### Audit Logging
- Structured event logging
- Compliance tracking
- Security monitoring
- Separate audit log file

## Environment Variables

- `GUARD_ENABLED` - Enable policy engine (default: true)
- `PII_DETECTION_ENABLED` - Enable PII detection (default: true)

## Usage

### Policy Engine

```python
from sheratan_guard.policy import PolicyEngine, PolicyAction

engine = PolicyEngine()

# Add custom rule
engine.add_rule(
    name="no_spam",
    condition=lambda ctx: "spam" in ctx.get("content", "").lower(),
    action=PolicyAction.DENY,
    message="Spam content not allowed"
)

# Evaluate
result = engine.evaluate({"content": "Some text"})
# Returns: {"decision": "allow", "rules_triggered": [], "messages": []}
```

### PII Detection

```python
from sheratan_guard.pii import PIIDetector

detector = PIIDetector()

text = "Contact me at john@example.com or 555-123-4567"

# Detect PII
pii = detector.detect(text)
# Returns: [{"type": "email", ...}, {"type": "phone", ...}]

# Redact PII
redacted = detector.redact(text)
# Returns: "Contact me at [REDACTED] or [REDACTED]"

# Full scan
report = detector.scan_and_report(text)
# Returns: {"has_pii": true, "pii_count": 2, ...}
```

### Audit Logging

```python
from sheratan_guard.audit import AuditLogger, AuditEventType

audit = AuditLogger()

# Log document ingest
audit.log_document_ingest(
    document_id="doc123",
    user_id="user456",
    success=True
)

# Log search
audit.log_search(
    query="search term",
    user_id="user456",
    results_count=10
)

# Log policy violation
audit.log_policy_violation(
    policy_name="no_spam",
    user_id="user456"
)
```

## Audit Log Format

Audit logs are written to `audit.log` in JSON format:

```json
{
  "timestamp": "2024-01-01T12:00:00.000000",
  "event_type": "document_ingest",
  "user_id": "user456",
  "resource_id": "doc123",
  "action": "ingest",
  "result": "success",
  "metadata": {}
}
```
