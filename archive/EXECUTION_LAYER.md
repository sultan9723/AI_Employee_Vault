# Execution Layer - Implementation Guide

## Overview

The execution layer is now complete. Here's what's implemented:

### New Component: `execution_handler.py`
- Detects task type (email, social, generic)
- Routes to appropriate handler
- Moves completed tasks to `Done/` or `Failed/`
- Gracefully skips if credentials missing

### Updated Component: `email_dispatcher.py`
- Now uses environment variables from `.env`
- Fallback if credentials not set
- Sends via SMTP (Gmail, Office 365, etc)

### Updated: `orchestrator.py`
- Added `execution_handler` to pipeline (position 8/11)
- Runs before email_dispatcher and webhooks

---

## Complete Task Flow

```
1. Inbox
   └─> Task arrives (email, form, webhook, etc)

2. Needs_Action
   └─> Raw task file created

3. Planner Agent
   └─> Creates execution plan in Plans/

4. Decision Maker Agent
   └─> Routes to READY_FOR_APPROVAL

5. Approval Gate Agent
   └─> Moves to Pending_Approval/ (waiting for human)

6. Human Review
   └─> Opens in Obsidian, reviews
   └─> Moves to Approved/ (manual copy)

7. Approved Watcher Agent
   └─> Detects file in Approved/
   └─> Moves to In_Progress/ ✅ EXECUTION STARTS HERE

8. LinkedIn Agent (if linkedin_social task)
   └─> Posts to LinkedIn (if credentials set)

9. Facebook Agent (if facebook_social task)
   └─> Posts to Facebook (if credentials set)

10. Odoo Agent (if odoo_invoice task)
    └─> Creates invoice in Odoo (if running)

11. Execution Handler ✅ NEW - MAIN EXECUTOR
    └─> Detects task type
    └─> If EMAIL → send via SMTP
    └─> If SOCIAL → log (social agents already posted)
    └─> If GENERIC → log completion
    └─> Move to Done/ ✅ SUCCESS

12. Email Dispatcher (alternative email path)
    └─> Optional: Additional email sending

13. Webhook Dispatcher
    └─> Send completion webhook (optional)

14. Status Snapshot
    └─> Update Dashboard.md with metrics

15. Done/
    └─> Task complete, logged, archived ✅
```

---

## Setup Instructions

### 1. Configure SMTP Credentials in `.env`

For **Gmail**:
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_RECIPIENT=your_email@gmail.com
```

**Important**: Use an [App Password](https://myaccount.google.com/apppasswords), not your regular Gmail password.

For **Office 365**:
```env
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=your_email@company.com
SMTP_PASSWORD=your_password
SMTP_RECIPIENT=your_email@company.com
```

### 2. Test Email Execution

**Method A: Manual Test**
```bash
# 1. Add a test task to Approved/
cp Approved/example_email_task.md

# 2. Run orchestrator
python orchestrator.py

# 3. Check logs
tail -f Logs/execution_handler.log
```

**Method B: Direct Test**
```bash
# Run execution handler directly
python agents/execution_handler.py
```

### 3. Verify Success

Check `Logs/execution_handler.log`:
```
2026-04-24 11:30:00 | INFO     | Execution Handler started
2026-04-24 11:30:00 | INFO     | Found 1 task(s) to execute

2026-04-24 11:30:01 | INFO     | 📋 Executing: example_email_task
2026-04-24 11:30:01 | INFO     |   Type: EMAIL
2026-04-24 11:30:02 | INFO     |   ✅ Email sent to your_email@gmail.com
2026-04-24 11:30:02 | INFO     |   ➡️  Moving to Done/

2026-04-24 11:30:02 | INFO     | Execution complete: 1/1 succeeded
```

Then check:
- ✅ Email received in inbox
- ✅ `Done/example_email_task.md` exists
- ✅ `Logs/execution_handler.log` has success entry

---

## Task Type Detection

The execution handler automatically detects task type:

### EMAIL Task
```markdown
# Send Report to Client

To: client@example.com
Subject: Monthly Report

Dear Client,
Please find attached your monthly report.
```

**Detected by:**
- Filename contains "email"
- Content has "to:", "recipient:", "send email"
- Type: EMAIL in frontmatter

### SOCIAL Task
```markdown
# Post to LinkedIn

type: social
platform: linkedin

Check out our new AI Employee system!
It's revolutionizing how we work.

#AI #Automation #Employment
```

**Detected by:**
- Contains: linkedin, facebook, twitter, instagram
- Type: social in frontmatter

### GENERIC Task
```markdown
# Generate Report

This is a generic task.
Just log completion and move to Done.
```

**Detected by:**
- Doesn't match email or social patterns
- Default fallback type

---

## Failure Handling

### If Credentials Missing
```
2026-04-24 11:30:00 | WARNING  | Email credentials not set
2026-04-24 11:30:00 | WARNING  | ⏭️  Skipping (SMTP_HOST, SMTP_USER, SMTP_PASSWORD, SMTP_RECIPIENT)
2026-04-24 11:30:00 | INFO     |   ➡️  Moving to Done/ (as skipped)
```

**Result:** Task moves to `Done/` but email not sent. Check logs.

### If Email Fails
```
2026-04-24 11:30:02 | ERROR    | Email failed: [Errno 550] user does not exist
2026-04-24 11:30:02 | INFO     |   ➡️  Moving to Failed/
```

**Result:** Task moves to `Failed/`. Review and retry manually.

---

## Integration with Other Agents

### LinkedIn Posting
When a `linkedin_post` task reaches `In_Progress/`:
1. LinkedIn Agent posts to profile
2. Execution Handler detects it's SOCIAL
3. Logs completion (LinkedIn agent already posted)
4. Moves to `Done/`

### Odoo Invoicing
When an `odoo_invoice` task reaches `In_Progress/`:
1. Odoo Agent creates invoice
2. Execution Handler detects it's generic
3. Logs completion
4. Moves to `Done/`

---

## Monitoring

### View Real-Time Logs
```bash
# All activity
tail -f Logs/activity.log

# Just execution handler
tail -f Logs/execution_handler.log

# Just email dispatcher
tail -f Logs/email_dispatcher.log
```

### Check Status
```bash
# See current queue
cat Dashboard.md | grep -A 10 "Task Queue"

# List in-progress tasks
ls In_Progress/ | wc -l

# List completed tasks
ls Done/ | wc -l

# List failed tasks
ls Failed/ | wc -l
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Email not sent | Check `Logs/execution_handler.log` for errors. Verify SMTP credentials in `.env`. |
| Task stuck in In_Progress | Check if a task is malformed. Look for errors in logs. Move to Failed/ manually. |
| "Authentication failed" | Gmail: Use [App Password](https://myaccount.google.com/apppasswords), not regular password. Office 365: Verify password. |
| Slow execution | Each agent has 60-second timeout. Check if network/APIs are slow. |

---

## Next Steps

After testing email:

1. **Enable Facebook**: Add `FACEBOOK_PAGE_ACCESS_TOKEN` and `FACEBOOK_PAGE_ID` to `.env`
2. **Enable LinkedIn**: Add `LINKEDIN_PERSON_URN` to `.env` (requires manual lookup)
3. **Enable Odoo**: Set up Docker Odoo 19 and add credentials to `.env`
4. **Set up webhooks**: Configure external services to POST to webhook endpoint
5. **Implement Ralph Wiggum Loop**: For multi-step task automation

---

## Architecture Summary

```
EXECUTION LAYER (agents/execution_handler.py)
├─ Detects Task Type
├─ Email Handler
│  └─ Uses SMTP to send
├─ Social Handler
│  └─ Delegates to LinkedIn/Facebook agents
├─ Generic Handler
│  └─ Logs only
└─ Moves to Done/ or Failed/

INTEGRATION
├─ Part of 11-agent orchestrator pipeline
├─ Runs every 30 seconds (CYCLE_INTERVAL_SECONDS)
├─ Position #8 (after social agents, before webhooks)
└─ Gracefully skips if credentials missing
```

---

**Status: EXECUTION LAYER COMPLETE ✅**

System can now:
- ✅ Receive tasks via email/forms
- ✅ Route through approval workflow
- ✅ Execute emails via SMTP
- ✅ Post to social media (LinkedIn, Facebook, Odoo)
- ✅ Track completion in Dashboard
- ✅ Handle failures gracefully

Ready for production testing! 🚀
