"""
Odoo MCP Agent - Integrates Odoo Community Edition with AI Employee
Creates invoices, retrieves accounting data, manages receivables

Setup:
1. Install Odoo 19 Community (https://www.odoo.com/documentation/19.0/setup/install)
   OR use Docker: docker run -d -p 8069:8069 odoo:19
2. Access http://localhost:8069 and create admin account
3. Enable Developer Mode: Settings → Activate Developer Mode
4. Get API Key: Settings → Users & Companies → Users → Admin → API Key
5. Set in .env:
   - ODOO_URL=http://localhost:8069
   - ODOO_DB=odoo
   - ODOO_USER=admin
   - ODOO_API_KEY=<your_api_key>

Approved file format for invoices:
---
type: odoo_invoice
customer: Client Name
amount: 1500.00
description: Service Description
---

Content here (optional notes)
"""

import os
import logging
from pathlib import Path
from datetime import datetime
import json

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, will use system env vars

# Configuration
BASE_DIR = Path(__file__).parent.parent
APPROVED_DIR = BASE_DIR / "Approved"
DONE_DIR = BASE_DIR / "Done"
LOGS_DIR = BASE_DIR / "Logs"
LOG_FILE = LOGS_DIR / "activity.log"


def setup_logging() -> logging.Logger:
    """Configure logging"""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("odoo_agent")
    logger.setLevel(logging.INFO)
    
    if logger.handlers:
        return logger
    
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


class OdooAgent:
    """Odoo integration via JSON-RPC API"""
    
    def __init__(self, url: str, db: str, username: str, api_key: str):
        """
        Initialize Odoo connection
        
        Args:
            url: Odoo base URL (e.g., http://localhost:8069)
            db: Database name (usually 'odoo')
            username: Admin username (usually 'admin')
            api_key: API key from Odoo settings
        """
        self.url = url
        self.db = db
        self.username = username
        self.api_key = api_key
        self.logger = setup_logging()
        self.uid = None
        self._authenticate()
        
    def _authenticate(self):
        """Authenticate with Odoo using API key"""
        try:
            import xmlrpc.client
            
            # Connect to authentication endpoint
            auth_url = f"{self.url}/jsonrpc"
            auth = xmlrpc.client.ServerProxy(auth_url, allow_none=True)
            
            # Call authenticate method
            result = auth.call({
                'service': 'common',
                'method': 'authenticate',
                'args': [self.db, self.username, self.api_key, {}]
            })
            
            if result:
                self.uid = result
                self.logger.info(f"✅ Authenticated with Odoo (UID: {self.uid})")
            else:
                self.logger.error("❌ Odoo authentication failed - invalid credentials")
                raise Exception("Authentication failed")
                
        except ImportError:
            self.logger.error("xmlrpc not available. This agent requires Python 3 built-in xmlrpc library")
            raise
        except Exception as e:
            self.logger.error(f"❌ Odoo connection failed: {e}")
            raise
    
    def create_invoice(self, partner_name: str, amount: float, description: str) -> int:
        """
        Create an invoice in Odoo
        
        Args:
            partner_name: Customer/partner name
            amount: Invoice amount
            description: Description of goods/services
            
        Returns:
            Invoice ID if successful, None otherwise
        """
        try:
            import xmlrpc.client
            
            models = xmlrpc.client.ServerProxy(f"{self.url}/jsonrpc", allow_none=True)
            
            # Find or create partner
            partners = models.call({
                'service': 'object',
                'method': 'execute',
                'args': [
                    self.db, self.uid, self.api_key, 'res.partner',
                    'search', [['name', '=', partner_name]]
                ]
            })
            
            if partners:
                partner_id = partners[0]
                self.logger.info(f"Using existing partner: {partner_name} (ID: {partner_id})")
            else:
                partner_id = models.call({
                    'service': 'object',
                    'method': 'execute',
                    'args': [
                        self.db, self.uid, self.api_key, 'res.partner',
                        'create', [{
                            'name': partner_name,
                            'customer_rank': 1,
                            'type': 'contact'
                        }]
                    ]
                })
                self.logger.info(f"Created new partner: {partner_name} (ID: {partner_id})")
            
            # Create invoice
            invoice_data = {
                'partner_id': partner_id,
                'move_type': 'out_invoice',
                'journal_id': 1,  # Default sales journal
                'invoice_line_ids': [[0, 0, {
                    'name': description,
                    'quantity': 1,
                    'price_unit': float(amount)
                }]]
            }
            
            invoice_id = models.call({
                'service': 'object',
                'method': 'execute',
                'args': [
                    self.db, self.uid, self.api_key, 'account.move',
                    'create', [invoice_data]
                ]
            })
            
            self.logger.info(f"✅ Invoice created (ID: {invoice_id}) - {partner_name}: ${amount:.2f}")
            return invoice_id
            
        except ImportError:
            self.logger.error("xmlrpc not available")
            return None
        except Exception as e:
            self.logger.error(f"❌ Invoice creation failed: {e}")
            return None
    
    def get_accounting_summary(self) -> dict:
        """Get revenue summary for the month"""
        try:
            import xmlrpc.client
            from datetime import datetime, timedelta
            
            models = xmlrpc.client.ServerProxy(f"{self.url}/jsonrpc", allow_none=True)
            
            # Get first day of current month
            today = datetime.now()
            month_start = datetime(today.year, today.month, 1).strftime('%Y-%m-%d')
            
            # Query invoices
            result = models.call({
                'service': 'object',
                'method': 'execute',
                'args': [
                    self.db, self.uid, self.api_key, 'account.move',
                    'search_read',
                    [
                        ['move_type', '=', 'out_invoice'],
                        ['state', 'in', ['draft', 'posted']],
                        ['invoice_date', '>=', month_start]
                    ],
                    ['amount_total', 'partner_id', 'invoice_date']
                ]
            })
            
            total_revenue = sum(inv.get('amount_total', 0) for inv in result)
            
            return {
                'total_revenue': total_revenue,
                'invoice_count': len(result),
                'currency': 'USD',
                'period': 'current_month'
            }
        except Exception as e:
            self.logger.error(f"Failed to get accounting summary: {e}")
            return {}


def process_odoo_tasks():
    """Process approved Odoo tasks (invoices, accounting entries)"""
    APPROVED_DIR.mkdir(parents=True, exist_ok=True)
    DONE_DIR.mkdir(parents=True, exist_ok=True)
    
    logger = setup_logging()
    
    # Get credentials
    odoo_url = os.getenv("ODOO_URL")
    odoo_db = os.getenv("ODOO_DB")
    odoo_user = os.getenv("ODOO_USER")
    odoo_api_key = os.getenv("ODOO_API_KEY")
    
    if not all([odoo_url, odoo_db, odoo_user, odoo_api_key]):
        logger.info("⏭️  Odoo credentials not fully set, skipping Odoo operations")
        return
    
    try:
        agent = OdooAgent(odoo_url, odoo_db, odoo_user, odoo_api_key)
    except Exception as e:
        logger.error(f"Could not initialize Odoo agent: {e}")
        return
    
    # Process invoice approvals
    for filepath in sorted(APPROVED_DIR.glob("*.md")):
        if "odoo" not in filepath.name.lower() and "invoice" not in filepath.name.lower():
            continue
        
        try:
            content = filepath.read_text(encoding="utf-8")
            
            # Parse YAML frontmatter
            parts = content.split("---")
            if len(parts) < 2:
                continue
            
            frontmatter = parts[1].strip()
            invoice_data = {}
            
            for line in frontmatter.split("\n"):
                if ": " in line:
                    key, value = line.split(": ", 1)
                    invoice_data[key.strip()] = value.strip()
            
            # Only process if it's marked as odoo invoice type
            if invoice_data.get("type") not in ["odoo_invoice", "invoice"]:
                continue
            
            # Extract invoice details
            customer = invoice_data.get("customer", "Unknown")
            amount_str = invoice_data.get("amount", "0")
            description = invoice_data.get("description", "Service")
            
            try:
                amount = float(amount_str)
            except ValueError:
                logger.error(f"Invalid amount in {filepath.name}: {amount_str}")
                continue
            
            # Create invoice
            logger.info(f"📤 Creating Odoo invoice: {filepath.name}")
            invoice_id = agent.create_invoice(customer, amount, description)
            
            if invoice_id:
                # Move to Done
                done_path = DONE_DIR / filepath.name
                filepath.rename(done_path)
                logger.info(f"✅ Moved to Done: {filepath.name}")
                
                # Log the action
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "action": "odoo_invoice",
                    "file": filepath.name,
                    "status": "success",
                    "invoice_id": invoice_id,
                    "customer": customer,
                    "amount": amount
                }
                logger.info(json.dumps(log_entry))
        
        except Exception as e:
            logger.error(f"Error processing {filepath.name}: {e}")


def main():
    """Main entry point"""
    logger = setup_logging()
    logger.info("Starting Odoo Agent...")
    process_odoo_tasks()
    logger.info("Odoo Agent completed")


if __name__ == "__main__":
    main()
