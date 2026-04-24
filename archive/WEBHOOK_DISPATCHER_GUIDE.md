# Webhook Dispatcher - Implementation Complete

## 📋 Overview

The `webhook_dispatcher.py` now implements **real webhook execution** with:
- ✅ Reads tasks from `/In_Progress` folder  
- ✅ Parses YAML frontmatter (type, url, payload)
- ✅ Sends HTTP POST requests with JSON payload
- ✅ Handles errors gracefully (keeps in `/In_Progress` for retry)
- ✅ Moves successful tasks to `/Done`
- ✅ Uses `requests` library (with `urllib` fallback)
- ✅ Full logging and error reporting

---

## 🚀 Quick Start

### 1. Get a Test Webhook URL

Visit **https://webhook.site** and copy your unique URL. It will look like:
```
https://webhook.site/4b9d9d64-5dff-4183-a9d5-760bd2d63c21
```

### 2. Create a Test Task

Create file: `/In_Progress/test_webhook.md`

```markdown
---
type: webhook
url: https://webhook.site/4b9d9d64-5dff-4183-a9d5-760bd2d63c21
---

# Send Test Webhook

## Payload

```json
{
  "message": "Hello from AI Employee",
  "timestamp": "2026-04-24",
  "action": "test"
}
```
```

### 3. Run the Dispatcher

```bash
python agents/webhook_dispatcher.py
```

### 4. Check Results

- ✅ If **successful**: Task moves to `/Done`, check logs
- ❌ If **failed**: Task stays in `/In_Progress`, will retry next cycle
- 📋 View webhook.site for incoming request

---

## 📝 Task File Format

```markdown
---
type: webhook
url: https://webhook.site/4b9d9d64-5dff-4183-a9d5-760bd2d63c21
status: pending
---

# Task Title

Description of what this webhook does.

## Payload

```json
{
  "key": "value",
  "nested": {
    "data": "structure"
  }
}
```
```

**Requirements:**
- `type: webhook` must be set in frontmatter
- `url:` must be a valid HTTPS endpoint
- Payload must be valid JSON (or plain text)

---

## 🔧 How It Works

### 1. **Parse Metadata**
```python
frontmatter = extract_frontmatter(content)
task_type = frontmatter.get("type")  # Must be "webhook"
url = frontmatter.get("url")         # Webhook endpoint
```

### 2. **Extract Payload**
- Looks for `## Payload` section in markdown
- Tries to parse as JSON
- Falls back to plain text if not JSON

### 3. **Send HTTP POST**
```python
requests.post(
    url,
    json=payload,
    headers={"Content-Type": "application/json"},
    timeout=30
)
```

### 4. **Move File**
- **Success (200-299)**: Move to `/Done`
- **Failure**: Keep in `/In_Progress` for retry

---

## 📊 Logging

All actions logged to: `Logs/webhook_dispatcher.log`

```
2026-04-24 12:00:00 | INFO     | Webhook Dispatcher Agent started
2026-04-24 12:00:00 | INFO     | Found 1 task(s)

2026-04-24 12:00:01 | INFO     | 📤 Webhook: test_webhook
2026-04-24 12:00:01 | INFO     |   🔗 URL: https://webhook.site/4b9d9d64-5dff-4183-a9d5-760bd2d63c21
2026-04-24 12:00:01 | INFO     |   📦 Payload: {"message": "Hello from AI Employee"}
2026-04-24 12:00:01 | INFO     |   📨 Sending via requests...
2026-04-24 12:00:02 | INFO     |   ✅ Webhook sent: Success (200)
2026-04-24 12:00:02 | INFO     |   ➡️  Moved to Done/

2026-04-24 12:00:02 | INFO     | Complete: 1/1 webhooks executed
```

---

## 🔄 Integration with Orchestrator

The webhook_dispatcher runs as **position #10** in the 11-agent pipeline:

```
1. planner
2. decision_maker
3. approval_gate
4. approved_watcher
5. linkedin_agent
6. facebook_agent
7. odoo_agent
8. execution_handler
9. email_dispatcher
10. webhook_dispatcher  ⭐ YOU ARE HERE
11. status_snapshot
```

### Execution Flow

```
Needs_Action/
    ↓
Plans/ (created by planner)
    ↓
Pending_Approval/ (human approval)
    ↓
Approved/ (human moves here)
    ↓
In_Progress/ (approved_watcher)
    ↓
webhook_dispatcher ← REAL EXECUTION
    ↓
Done/ (on success)
    ↓
Logs/ (all actions logged)
```

---

## 💡 Examples

### Example 1: Discord Webhook

```markdown
---
type: webhook
url: https://discordapp.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_TOKEN
---

# Post to Discord

## Payload

```json
{
  "content": "AI Employee just completed a task!",
  "username": "AI Employee",
  "avatar_url": "https://cdn-icons-png.flaticon.com/512/4436/4436481.png"
}
```
```

### Example 2: Slack Webhook

```markdown
---
type: webhook
url: https://hooks.slack.com/services/YOUR/WEBHOOK/URL
---

# Post to Slack

## Payload

```json
{
  "text": "Task completed!",
  "blocks": [
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*Task Complete* ✅\nThe AI Employee finished processing."
      }
    }
  ]
}
```
```

### Example 3: Custom API

```markdown
---
type: webhook
url: https://api.example.com/v1/actions
---

# Send to Custom API

## Payload

```json
{
  "action": "create_record",
  "data": {
    "name": "Automated Task",
    "status": "completed",
    "timestamp": "2026-04-24T12:00:00Z"
  }
}
```
```

---

## ⚙️ Configuration

### .env Variables (if needed)

Currently, webhook URLs are specified per-task in the markdown frontmatter. No .env setup required.

### HTTP Timeout

Set in `webhook_dispatcher.py`:
```python
WEBHOOK_TIMEOUT = 30  # seconds
```

### Retry Behavior

- Failed webhooks **stay in `/In_Progress`**
- System retries on next cycle (every 10-30 seconds)
- No limit on retry attempts

---

## 🧪 Testing

### Test 1: Valid Webhook

```bash
# Create task with webhook.site URL
# Run dispatcher
# Should move to Done/ and appear on webhook.site
```

### Test 2: Invalid URL

```bash
# Create task with bad URL (e.g., https://invalid.com)
# Run dispatcher
# Should stay in In_Progress/, log connection error
```

### Test 3: Malformed JSON

```bash
# Create task with invalid JSON in payload
# Run dispatcher
# Should fail, stay in In_Progress/, log error
```

---

## 📈 Next Steps

1. ✅ **webhook_dispatcher.py** - COMPLETE
2. ⬜ **Testing** - Create test task and verify
3. ⬜ **Integration** - Run full orchestrator cycle
4. ⬜ **Documentation** - Done!

---

## 🔗 Related Files

- [orchestrator.py](orchestrator.py) - Main pipeline
- [agents/execution_handler.py](agents/execution_handler.py) - Task type detection
- [agents/email_dispatcher.py](agents/email_dispatcher.py) - Email execution
- [agents/status_snapshot.py](agents/status_snapshot.py) - Dashboard updates

---

**Status: Ready for Testing** ✅
