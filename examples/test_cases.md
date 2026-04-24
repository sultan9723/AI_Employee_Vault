# Test Cases

## Webhook
`python run_ai_employee.py "System is down, alert the team"`

Expected decision: `webhook`

## Email
`python run_ai_employee.py "Please reply to this customer email"`

Expected decision: `email`

## Ignore
`python run_ai_employee.py "Just logging this note"`

Expected decision: `ignore`
