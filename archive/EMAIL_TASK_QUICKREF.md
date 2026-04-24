# Email_Task Quick Reference

## Create an Email-Task

### Template
```markdown
---
type: email_task
action: [webhook|email|generic]
url: https://webhook.site/4b9d9d64-5dff-4183-a9d5-760bd2d63c21
intent: Brief description of the task
---

# Task Title

Task content here...
```

## Supported Actions

### 1. Webhook Action
Sends HTTP POST to external URL:
```markdown
---
type: email_task
action: webhook
url: https://webhook.site/4b9d9d64-5dff-4183-a9d5-760bd2d63c21
intent: Send notification
---

## Payload
```json
{"message": "Task executed"}
```

- ✅ Automatically sends JSON POST
- ✅ Validates URL (http/https required)
- ✅ 30-second timeout
- ✅ Success: HTTP 200-299 → Done/
- ✅ Failure: Any error → Failed/

### 2. Email Action
Sends SMTP email to configured recipient:
```markdown
---
type: email_task
action: email
intent: Send daily report
---

Report content becomes email body.
Intent becomes subject line.
```

- ✅ Uses: SMTP_HOST, SMTP_USER, SMTP_PASSWORD, SMTP_RECIPIENT
- ✅ Requires: .env configuration
- ✅ Skips gracefully if credentials missing

### 3. Generic Action
Logs completion, no external action:
```markdown
---
type: email_task
action: generic
intent: Record task completion
---

Task content...
```

- ✅ Always succeeds
- ✅ Just logs the intent

## Where Tasks Go

1. **Create** in Needs_Action/ → Gets planned
2. **Approve** in Pending_Approval/ → Moved by human
3. **Execute** in In_Progress/ → Execution handler processes
4. **Result**:
   - Success → Done/
   - Failure → Failed/

## Example: Real Webhook Integration

```markdown
---
type: email_task
action: webhook
url: https://webhook.site/4b9d9d64-5dff-4183-a9d5-760bd2d63c21
intent: Send approval notification to external system
---

# Notify External System

When approved, this task sends a webhook to the external system.

## Payload

```json
{
  "system": "AI Employee",
  "event": "task_approved",
  "task_id": "task_001",
  "timestamp": "2026-04-25",
  "action": "notify_stakeholders"
}
```
```

## Minimal Example

```markdown
---
type: email_task
action: webhook
url: https://webhook.site/4b9d9d64-5dff-4183-a9d5-760bd2d63c21
---

Minimal task - will auto-generate payload with this content.
```

## Testing

1. Save task as: In_Progress/test_email_task.md
2. Run: python agents/execution_handler.py
3. Check logs: tail Logs/execution_handler.log
4. Verify: Task moved to Done/ or Failed/

---

**New Feature**: Email-style task definitions automatically converted to executable actions
**Type**: email_task
**Actions**: webhook | email | generic
**Status**: ✅ Ready to use
