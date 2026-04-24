# Message Cleaning Quick Reference

## What Changed
Added intelligent message extraction to `webhook_dispatcher.py` that cleans email content before sending to webhooks.

## Before vs After

### Before (Raw)
```
{
  "message": "# Header\n\nSubject: Title\nBody: Content\n\nMore text"
}
```

### After (Cleaned)
```
{
  "message": "Header Title Content More text"
}
```

## Cleaning Features

✅ Removes email labels: `Subject:`, `Body:`, `To:`, `From:`, `Date:`, `CC:`, `BCC:`  
✅ Removes markdown headers: `#`, `##`, `###`, etc.  
✅ Removes formatting lines: `---`, `***`, `___`  
✅ Removes extra whitespace  
✅ Joins into single-line message  
✅ Preserves meaningful content  

## Example Input/Output

### Input
```markdown
## Body

Subject: System Alert
Body: Database backup complete

Backup Size: 2.5GB
Duration: 45 minutes
Status: Success
```

### Output Payload
```json
{
  "message": "System Alert Database backup complete Backup Size: 2.5GB Duration: 45 minutes Status: Success"
}
```

## Console Output

```
📤 Processing: task_name
  📧 Found Body section: 145 chars
  🧹 Cleaning message from Body section...
  ✅ Extracted message: System Alert Database backup...
  📦 Clean payload: {"message": "System Alert..."}
  ✅ Converted email_task → webhook
     URL: https://webhook.site/4b9d9d64-5dff-4183-a9d5-760bd2d63c21
     Message length: 98 chars
```

## Logging

Check `Logs/webhook_dispatcher.log`:

```
[DEBUG] [CLEAN] Original: 145 chars
[DEBUG] [CLEAN] Cleaned: 98 chars
[INFO] ✅ Extracted message: System Alert Database...
[INFO] 📦 Clean payload: {"message": "System Alert..."}
```

## Task Format (Unchanged)

```markdown
---
type: email_task
action: webhook
url: https://webhook.site/4b9d9d64-5dff-4183-a9d5-760bd2d63c21
---

# Task Title

## Body

Your email content here.
Labels and headers will be cleaned automatically.
```

## Key Improvements

| Aspect | Before | After |
|--------|--------|-------|
| Email labels | Preserved | Removed |
| Markdown | Preserved | Removed |
| Line breaks | Multiple | Single |
| Readability | Poor | Excellent |
| Webhook UX | Complex | Clean |
| Char count | ~300+ | ~100-200 |

## Nothing to Change!

The improvement is **automatic**. Just create email_task files normally:

1. ✅ No code changes needed
2. ✅ No new fields required
3. ✅ No new format needed
4. ✅ Existing tasks still work
5. ✅ Backward compatible

The cleaning happens transparently during execution.

## Testing Example

File: `In_Progress/email_task_message_cleaning_example.md`

Run: `python agents/webhook_dispatcher.py`

Watch for: "🧹 Cleaning message from Body section..."

## How It Works

```
Raw Body Content
    ↓
Remove email labels (Subject:, Body:, etc.)
    ↓
Remove markdown headers (#, ##, etc.)
    ↓
Remove formatting lines (---, ***, etc.)
    ↓
Join lines into single message
    ↓
Remove extra spaces
    ↓
Trim whitespace
    ↓
Clean Payload
```

## Status

✅ **Complete**  
✅ **Ready to Use**  
✅ **No Changes Required**  
✅ **Backward Compatible**  

---

**Modified**: agents/webhook_dispatcher.py  
**Added**: clean_email_message() function  
**Impact**: Better webhook payloads  
**Usage**: Automatic - no action needed
