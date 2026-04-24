# Email_Task → Webhook Quick Reference

## What Changed
Modified `webhook_dispatcher.py` to automatically convert `email_task` type with `action: webhook` into executable webhook requests.

## Before (Skipped)
```
Tasks with type: email_task
    → webhook_dispatcher skips
    → execution_handler must handle
```

## After (Executed)
```
Tasks with type: email_task + action: webhook
    → webhook_dispatcher detects
    → Converts to webhook format
    → Sends HTTP POST automatically
```

## Task Format

### Simple Email_Task with Webhook

```markdown
---
type: email_task
action: webhook
url: https://webhook.site/4b9d9d64-5dff-4183-a9d5-760bd2d63c21
---

# Send Notification

Some description here...

## Body

This is the message that will be sent to the webhook.

It can be multiple lines.

The webhook will receive:
```json
{
  "message": "This is the message that will be sent to the webhook.\n\nIt can be multiple lines."
}
```

## Execution

1. Place in `In_Progress/`
2. Run: `python agents/webhook_dispatcher.py`
3. Dispatcher sees `type: email_task`
4. Logs: "🔄 Converting email_task → webhook..."
5. Extracts Body content
6. Sends HTTP POST: `{"message": "..."}`
7. Success: Moves to `Done/`
8. Failure: Keeps in `In_Progress/` (retry)

## Console Output

```
📤 Processing: my_email_task
  🔄 Converting email_task → webhook...
     Converted to webhook
  📦 Extracting payload...
  📨 Sending HTTP POST...
  ✅ SUCCESS: HTTP 200
  ➡️  MOVED: Done/
```

## Key Points

✅ `type: email_task` required  
✅ `action: webhook` required  
✅ `url:` must start with http:// or https://  
✅ `## Body` section content = webhook message  
✅ Payload always: `{"message": "..."}`  
✅ Same logging as regular webhooks  
✅ HTTP 200-299 = success  

## Multiple Examples

### Example 1: Simple Body
```markdown
---
type: email_task
action: webhook
url: https://webhook.site/4b9d9d64-5dff-4183-a9d5-760bd2d63c21
---

## Body
Alert: System task completed successfully
```

Sends: `{"message": "Alert: System task completed successfully"}`

### Example 2: Multi-Line Body
```markdown
---
type: email_task
action: webhook
url: https://webhook.site/4b9d9d64-5dff-4183-a9d5-760bd2d63c21
---

## Body
Task Status Report
==================

- Task ID: task_123
- Status: Completed
- Duration: 2 hours
- Result: Success
```

Sends: `{"message": "Task Status Report\n==================\n\n- Task ID: task_123\n..."}`

### Example 3: No Body Section (Fallback)
```markdown
---
type: email_task
action: webhook
url: https://webhook.site/4b9d9d64-5dff-4183-a9d5-760bd2d63c21
---

# Task Title

This content after frontmatter will be used as the message
if no ## Body section exists.
```

Sends: `{"message": "# Task Title\n\nThis content after frontmatter..."}`

## Logging

Check logs: `Logs/webhook_dispatcher.log`

Search for:
- `Converted email_task → webhook` - Successful conversion
- `email_task conversion failed` - Conversion error
- `HTTP 200` - Successful send
- `Connection error` - Network issue

## Status

✅ Feature Complete  
✅ Backward Compatible  
✅ Ready to Use  
✅ Production Ready

---

**Modified File**: agents/webhook_dispatcher.py  
**New Function**: extract_email_task_for_webhook()  
**Type Support**: email_task with action: webhook
