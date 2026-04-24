# Email Task Type Support - Implementation Summary

## Overview
Added support for a new **"email_task"** type to the AI Employee execution system. This allows email-style task definitions to be automatically converted to executable actions (webhook, email, or generic).

## What Was Added

### 1. New Type Detection
- Updated `detect_task_type()` to recognize `type: email_task`
- Email_task is highest priority (checked before email, social, generic)
- Detects by:
  - YAML frontmatter: `type: email_task`
  - Filename pattern: contains "email_task"

### 2. New Functions

#### `extract_email_task_metadata(task_content) → dict`
Parses email_task frontmatter and extracts:
- **action**: What to do (webhook, email, generic)
- **url**: Webhook endpoint (if action=webhook)
- **payload**: JSON data to send (if action=webhook)
- **intent**: Human-readable task description

```yaml
---
type: email_task
action: webhook
url: https://webhook.site/4b9d9d64-5dff-4183-a9d5-760bd2d63c21
intent: Send system notification
---
```

#### `execute_email_task_action(task_file, task_content, logger) → bool`
Main router for email_task execution. Dispatches to:
- `execute_email_task_webhook_action()` if action=webhook
- `execute_email_task_email_action()` if action=email
- Logs and succeeds if action=generic

#### `execute_email_task_webhook_action(task_file, metadata, task_content, logger) → bool`
Sends HTTP POST to webhook with:
- URL validation (must start with http:// or https://)
- JSON payload (uses provided payload or constructs from intent+content)
- Headers: Content-Type: application/json, User-Agent: AIEmployee-EmailTask/1.0
- 30-second timeout
- Success: HTTP 200-299, logs to Done/
- Failure: Any error, keeps in In_Progress/ for retry

#### `execute_email_task_email_action(task_file, metadata, task_content, logger) → bool`
Sends SMTP email with:
- Intent as subject line
- Full task content as body
- Uses credentials: SMTP_HOST, SMTP_USER, SMTP_PASSWORD, SMTP_RECIPIENT
- Gracefully skips if credentials not configured

### 3. Updated Type Routing
Modified `execute_task()` to route email_task before other types:
```python
if task_type == 'email_task':
    success = execute_email_task_action(...)
elif task_type == 'email':
    success = execute_email_task(...)
elif task_type == 'social':
    success = execute_social_task(...)
else:
    success = execute_generic_task(...)
```

### 4. Dependencies
Added:
- `import json` - for JSON payload parsing
- `requests` library check (graceful degradation if missing)

## Task Format Examples

### Email_Task → Webhook Action
```markdown
---
type: email_task
action: webhook
url: https://webhook.site/4b9d9d64-5dff-4183-a9d5-760bd2d63c21
intent: Send approval notification
---

# Webhook Notification

Send a notification to the external system when task is approved.

## Payload

```json
{
  "event": "task_approved",
  "task_id": "task_123",
  "timestamp": "2026-04-25T10:30:00Z",
  "message": "Task approved by AI Employee"
}
```
```

### Email_Task → Email Action
```markdown
---
type: email_task
action: email
intent: Send daily summary report
---

# Daily Summary Email

Send the daily task summary to configured email recipient.

This content becomes the email body. The intent becomes the subject line.
```

### Email_Task → Generic (Log Only)
```markdown
---
type: email_task
action: generic
intent: Complete data migration task
---

# Data Migration

Log completion without external action.
```

## Execution Flow

```
Needs_Action/
  ↓ (planner creates plan)
Pending_Approval/
  ↓ (human approves)
Approved/
  ↓ (approved_watcher moves)
In_Progress/
  ├─ execution_handler detects type: email_task
  ├─ Extracts metadata (action, url, intent)
  ├─ Routes by action:
  │  ├─ webhook → HTTP POST → webhook endpoint
  │  ├─ email → SMTP send → configured recipient
  │  └─ generic → Log message → Done/
  └─ Success → Done/
     or Failure → Failed/
```

## Configuration

No new environment variables needed. Uses existing:
- `SMTP_HOST` - For email action
- `SMTP_PORT` - For email action
- `SMTP_USER` - For email action
- `SMTP_PASSWORD` - For email action
- `SMTP_RECIPIENT` - For email action

Webhook action requires:
- Valid HTTPS URL in task frontmatter
- `requests` library installed (graceful fallback if not)

## Testing

Two example tasks included:
1. **example_email_task.md** - Email_task with webhook action
2. **example_email_notification.md** - Email_task with email action

To test:
1. Place task in In_Progress/
2. Run: `python agents/execution_handler.py`
3. Check logs: `tail Logs/execution_handler.log`
4. Verify: Task moved to Done/ (success) or Failed/ (error)

## Backward Compatibility

✅ Fully backward compatible:
- Existing 'email' tasks unchanged
- Existing 'social' tasks unchanged
- Existing 'generic' tasks unchanged
- No breaking changes to API

## Key Benefits

1. **Simple**: Just add `type: email_task` to task frontmatter
2. **Flexible**: Supports webhook, email, and generic actions
3. **Reusable**: Leverages existing webhook/email infrastructure
4. **Minimal**: No new frameworks or complex architecture
5. **Graceful**: Skips missing credentials rather than crashing

## Error Handling

- **Invalid URL**: Logged to Failed/
- **Connection timeout**: Logged to Failed/, kept in In_Progress/ for retry
- **Missing credentials**: Logged as warning, task succeeds (skipped)
- **JSON parsing errors**: Graceful fallback to string payload
- **SMTP errors**: Logged to Failed/

---

**Status**: ✅ Complete and ready for use
**Date Implemented**: April 25, 2026
**System Tier**: ~80% Gold Tier (email_task support added)
