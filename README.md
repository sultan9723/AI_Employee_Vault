# AI Email-to-Action Agent

A decision-driven automation system that converts natural language instructions into executable actions using an LLM-powered decision layer and a deployed API.

---

## Problem

Operational workflows often rely on humans to interpret incoming messages and trigger actions.

Examples:

* "System is down, alert the team"
* "Reply to this client email"
* "I need help with my order"

This introduces:

* delays in response
* manual overhead
* inconsistent execution
* limited scalability

There is no standardized system that converts unstructured input into deterministic, executable operations.

---

## Solution

This project implements a  automation system that:

* accepts natural language input
* uses an LLM (Gemini API) to determine intent
* routes the request to an appropriate action
* executes the action via external integrations
* returns a structured response

The system is exposed as a public API, making it usable as a backend service for automation workflows.

---

## Architecture

```
                ┌──────────────────────┐
                │      Client          │
                │  (CLI / API Call)    │
                └─────────┬────────────┘
                          │
                          ▼
                ┌──────────────────────┐
                │   LLM Decision Layer │
                │   (Gemini API)       │
                └─────────┬────────────┘
                          │
                          ▼
                ┌──────────────────────┐
                │    Action Router     │
                └─────────┬────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Webhook     │  │   Email      │  │   Support    │
│  (HTTP POST) │  │ (Simulated)  │  │  (Response)  │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       └──────────┬──────┴──────┬──────────┘
                  ▼             ▼
            ┌────────────────────────┐
            │   Execution Result     │
            └────────────────────────┘
```

---

## Core Components

### Input Layer

Accepts input via:

* CLI (`run_ai_employee.py`)
* REST API (`POST /run`)

---

### LLM Decision Layer

Uses Gemini API to classify messages into actions:

* webhook
* email
* support
* ignore

This enables semantic understanding instead of keyword-based matching.

---

### Action Layer

| Action  | Description                           |
| ------- | ------------------------------------- |
| webhook | Sends HTTP POST request to endpoint   |
| email   | Simulates sending an email            |
| support | Generates contextual support response |
| ignore  | No operation                          |

---

### Execution Layer

Handles real-world interaction and returns structured output.

Example response:

```
{
  "decision": "webhook",
  "result": "Status code: 200",
  "success": true
}
```

---

### API Layer

Built using FastAPI.

#### Endpoint

```
POST /run
```

#### Request

```
{
  "message": "System is down"
}
```

#### Response

```
{
  "decision": "webhook",
  "result": "Status code: 200",
  "success": true
}
```

---

## Live API

Base URL:

```
https://ai-employee-vault-0m22.onrender.com
```

Test:

```
POST /run
```

---

## Example Usage

### CLI

```
python run_ai_employee.py "System is down, alert the team"
```

### API (PowerShell)

```
Invoke-RestMethod -Uri "https://ai-employee-vault-0m22.onrender.com/run" `
-Method Post `
-Headers @{ "Content-Type" = "application/json" } `
-Body '{"message":"I need help with my order"}'
```

---

## Project Structure

```
api.py
run_ai_employee.py
llm_decision.py
requirements.txt
```

---

## Design Principles

* minimal dependencies for reliable deployment
* separation of decision and execution logic
* API-first architecture for integration
* LLM used only where it adds value (decision layer)

---

## Limitations

* no persistent memory or state
* email execution is simulated
* single-step execution
* dependent on external LLM API

---

## Future Direction

* add memory and contextual understanding
* integrate real email and communication systems
* support multi-step workflows
* enable autonomous task chaining
* add monitoring and logging layer

---

## Summary

This project demonstrates how natural language can be transformed into real-world actions using a combination of LLM-based decision-making and a modular execution system.

It provides a foundation for building practical AI-driven automation systems.

---

## Author

Sultan Qaiser

AI engineering .
