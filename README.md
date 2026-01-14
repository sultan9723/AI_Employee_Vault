# 🤖 AI Employee Vault

> **An autonomous AI employee that reads tasks, thinks through decisions, and asks for approval — all powered by Claude Code and Obsidian.**

Built for the **2026 Personal AI Employee Hackathon**

---

## 💡 What Is This?

Imagine hiring a junior employee who:
- Reads incoming emails and messages
- Figures out what needs to be done
- Drafts plans and responses
- Asks you before taking action
- Keeps perfect records of everything

**That's exactly what this system does — but the employee is an AI.**

The AI Employee monitors a folder-based inbox, evaluates each task, creates execution plans, and routes decisions through human approval before acting. It's autonomous, but never goes rogue.

---

## 🧠 The Brain: Claude Code

**Claude Code** serves as the reasoning engine — the AI's brain.

When a new task arrives, Claude:
1. Reads and understands the request
2. Determines urgency and complexity
3. Creates a step-by-step execution plan
4. Identifies what requires human approval
5. Writes clear reasoning for every decision

Claude follows strict rules defined in `CLAUDE.md` — acting conservatively and always preferring human oversight for sensitive actions.

```
"Be conservative. Prefer human approval. Never act without explicit authorization."
```

---

## 📚 The Memory: Obsidian Vault

**Obsidian** acts as the AI's memory, workspace, and dashboard.

The entire system lives in an Obsidian vault — a collection of markdown files organized into folders:

| Folder | Purpose |
|--------|---------|
| `Inbox/` | New tasks arrive here |
| `Needs_Action/` | Tasks awaiting AI processing |
| `Plans/` | Execution plans created by the AI |
| `Pending_Approval/` | Decisions waiting for human sign-off |
| `Approved/` | Manager-approved actions |
| `Done/` | Completed tasks |
| `Logs/Reasoning/` | Full audit trail of AI decisions |

This structure means:
- ✅ Everything is human-readable (no databases)
- ✅ Full transparency into AI thinking
- ✅ Easy to review, edit, or override
- ✅ Works offline with local files

---

## 🔄 How Tasks Flow Through the System

```
┌─────────────┐
│   CLIENT    │  (sends email/WhatsApp)
└──────┬──────┘
       ▼
┌─────────────┐
│   INBOX     │  Task lands as markdown file
└──────┬──────┘
       ▼
┌─────────────┐
│ NEEDS_ACTION│  AI evaluates the task
└──────┬──────┘
       ▼
┌─────────────┐
│   PLANS     │  AI creates execution plan
└──────┬──────┘
       ▼
┌─────────────┐
│  PENDING    │  AI requests human approval
│  APPROVAL   │
└──────┬──────┘
       ▼
┌─────────────┐
│  HUMAN      │  Manager reviews & approves
│  DECISION   │
└──────┬──────┘
       ▼
┌─────────────┐
│   DONE      │  Task completed & logged
└─────────────┘
```

**Example:** A client emails asking for a quote → AI reads the request → Creates itemized quote → Submits for manager approval → Manager approves → AI sends quote → Task archived.

---

## 👤 Human-in-the-Loop: You Stay in Control

The AI Employee is designed to **assist, not replace** human judgment.

### When does the AI ask for approval?

| Action Type | AI Behavior |
|-------------|-------------|
| Reading/analyzing tasks | ✅ Autonomous |
| Creating plans | ✅ Autonomous |
| Internal calculations | ✅ Autonomous |
| **Client communication** | 🔒 Requires approval |
| **Financial decisions** | 🔒 Requires approval |
| **Commitments/contracts** | 🔒 Requires approval |

### How approval works:

1. AI creates a formal approval request in `Pending_Approval/`
2. Request includes: summary, proposed action, and reasoning
3. Human reviews and selects: **Approve / Modify / Reject**
4. AI only proceeds after explicit authorization

This ensures the AI handles the busywork while humans make the important calls.

---

## 🏆 Why This Matters

| Traditional Automation | AI Employee Vault |
|------------------------|-------------------|
| Rigid rules | Understands context |
| Breaks on edge cases | Reasons through ambiguity |
| No explanation | Full reasoning logs |
| All-or-nothing | Human approval checkpoints |
| Technical setup | Plain markdown files |

This system demonstrates that **AI employees can be practical today** — not as science fiction, but as useful tools that augment human work.

---

## 📁 Project Structure

```
AI_Employee_Vault/
├── Inbox/                  # New incoming tasks
├── Needs_Action/           # Tasks being processed
├── Plans/                  # AI-generated execution plans
├── Pending_Approval/       # Awaiting human sign-off
├── Approved/               # Authorized actions
├── Done/                   # Completed work
├── Rejected/               # Declined tasks
├── Logs/Reasoning/         # Decision audit trail
├── agents/                 # Python automation scripts
├── watchers/               # File system monitors
├── CLAUDE.md               # AI behavior rules
├── Company_Handbook.md     # Business context
├── Business_Goals.md       # Strategic objectives
└── Dashboard.md            # Status overview
```

---

## 🚀 Quick Demo

1. Drop a task file into `Inbox/`
2. Watch the AI read it, plan a response, and request approval
3. Review the approval request in `Pending_Approval/`
4. Approve it — task completes automatically

---

## 🛠 Built With

- **Claude Code** — AI reasoning and decision-making
- **Obsidian** — Knowledge management and dashboard
- **Python** — File watchers and task routing
- **Markdown** — Universal, human-readable format

---

## 👥 Team

Built with ❤️ for the 2026 Personal AI Employee Hackathon

---

*"The best AI employee is one that knows when to ask for help."*

This system demonstrates how an AI employee can reason, act, and justify decisions responsibly.
