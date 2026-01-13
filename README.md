# AI Employee Vault

An autonomous AI-inspired employee system that ingests tasks, evaluates them, makes decisions, and records reasoning — built for the **2026 Personal AI Employee Hackathon**.

---

## What This AI Employee Does

This system acts like a junior operations employee:

- Monitors incoming work
- Decides what needs action
- Approves or flags tasks
- Explains *why* each decision was made
- Maintains a full audit trail

---

## How It Works (Simple Flow)

1. A task file enters `Inbox/`
2. A watcher moves it to `Needs_Action/`
3. The classifier reads task content
4. The system decides:
   - Needs_Action
   - Approved
   - Pending_Approval
5. A reasoning report is generated
6. All actions are logged with timestamps

---

## Example Decision

**Task:** `task_001.md`  
**Decision:** NEEDS_ACTION  
**Reason:** Task content was empty or missing required information.

(See `Logs/Reasoning/` for full decision records.)

---

## Why This Qualifies as an AI Employee

- Autonomous behavior (no manual triggers)
- Decision-making logic
- Explainable reasoning
- Audit logs
- AI-ready architecture (rules can be replaced with LLMs)

This system demonstrates how an AI employee can reason, act, and justify decisions responsibly.
