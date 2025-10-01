from typing import Dict, Any, List
import csv
import os
import json
import glob
from langchain_core.documents import Document


def load_json_documents_from_dir(dir_path: str) -> List[Document]:
    docs: List[Document] = []
    for fp in glob.glob(os.path.join(dir_path, "*.json")):
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        if isinstance(data, list):
            for i, item in enumerate(data):
                text = json.dumps(item, ensure_ascii=False)
                docs.append(
                    Document(
                        page_content=text,
                        metadata={
                            "source": os.path.basename(fp),
                            "index": i,
                            "category": "CompanyPolicy",
                        },
                    )
                )
        elif isinstance(data, dict):
            text = json.dumps(data, ensure_ascii=False)
            docs.append(
                Document(
                    page_content=text,
                    metadata={
                        "source": os.path.basename(fp),
                        "category": "CompanyPolicy",
                    },
                )
            )
    return docs


def load_json_documents(file_paths: List[str]) -> List[Document]:
    docs: List[Document] = []
    for fp in file_paths:
        if not os.path.exists(fp):
            continue
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        if isinstance(data, list):
            for i, item in enumerate(data):
                text = json.dumps(item, ensure_ascii=False)
                docs.append(
                    Document(
                        page_content=text,
                        metadata={
                            "source": os.path.basename(fp),
                            "index": i,
                            "category": "CompanyPolicy",
                        },
                    )
                )
        elif isinstance(data, dict):
            text = json.dumps(data, ensure_ascii=False)
            docs.append(
                Document(
                    page_content=text,
                    metadata={
                        "source": os.path.basename(fp),
                        "category": "CompanyPolicy",
                    },
                )
            )
    return docs


# Base knowledge base documents (from the notebook)
_base_knowledge_documents: List[Document] = [
    Document(
        page_content=(
            "To reset your password, go to the login page and click 'Forgot Password'. "
            "Enter your email address and check your inbox for reset instructions. "
            "The reset link expires in 24 hours."
        ),
        metadata={"category": "Account", "topic": "Password Reset", "priority": "High"},
    ),
    Document(
        page_content=(
            "For billing issues, you can view your invoices in the Billing section of your account "
            "dashboard. Payment methods can be updated under Account Settings > Payment Information. "
            "Refunds are processed within 5-7 business days."
        ),
        metadata={"category": "Billing", "topic": "Payment Management", "priority": "High"},
    ),
    Document(
        page_content=(
            "Our API rate limits are 1000 requests per hour for Basic plans, 5000 for Premium, and "
            "10000 for Enterprise. If you exceed these limits, you'll receive a 429 status code. "
            "Consider upgrading your plan for higher limits."
        ),
        metadata={"category": "Technical", "topic": "API Limits", "priority": "Medium"},
    ),
    Document(
        page_content=(
            "To integrate our API, use the base URL https://api.ourcompany.com/v1. Authentication "
            "requires an API key in the Authorization header. Example: Authorization: Bearer your_api_key_here"
        ),
        metadata={"category": "Technical", "topic": "API Integration", "priority": "High"},
    ),
    Document(
        page_content=(
            "Data export is available for all plans. Go to Account Settings > Data Export to request your data. "
            "The export will be emailed to you within 24 hours and includes all your account data in JSON format."
        ),
        metadata={"category": "Account", "topic": "Data Export", "priority": "Medium"},
    ),
    Document(
        page_content=(
            "Two-factor authentication (2FA) can be enabled in Security Settings. We support SMS, email, and "
            "authenticator apps. 2FA is required for Enterprise accounts and recommended for all users."
        ),
        metadata={"category": "Account", "topic": "Security", "priority": "High"},
    ),
    Document(
        page_content=(
            "Subscription upgrades take effect immediately. Downgrades take effect at the next billing cycle. "
            "You can change your plan anytime in Account Settings > Subscription Management."
        ),
        metadata={"category": "Billing", "topic": "Plan Changes", "priority": "Medium"},
    ),
    Document(
        page_content=(
            "Our service status page is available at status.ourcompany.com. We post real-time updates about any "
            "service disruptions, maintenance windows, or performance issues."
        ),
        metadata={"category": "Technical", "topic": "Service Status", "priority": "High"},
    ),
    Document(
        page_content=(
            "For enterprise customers, we offer dedicated support channels including phone support, dedicated "
            "account managers, and custom SLA agreements. Contact sales@ourcompany.com for more information."
        ),
        metadata={"category": "General", "topic": "Enterprise Support", "priority": "Low"},
    ),
    Document(
        page_content=(
            "Webhook configuration is available in the Developer section. You can set up webhooks for events like "
            "payment success, user registration, and data updates. Webhook URLs must use HTTPS."
        ),
        metadata={"category": "Technical", "topic": "Webhooks", "priority": "Medium"},
    ),
]


# Auto-include two specific JSON files under project data directory
_project_root = os.path.dirname(os.path.dirname(__file__))
_data_dir = os.path.join(_project_root, "data")
_specific_json_files = [
    os.path.join(_data_dir, "승하차정보.json"),
    os.path.join(_data_dir, "통근수당.json"),
]
_specific_docs = load_json_documents(_specific_json_files)

# Final knowledge base used by tools: ONLY specific JSON docs
knowledge_base_documents: List[Document] = _specific_docs


# Specialist routing info
specialists: Dict[str, Dict[str, Any]] = {
    "Technical": {
        "specialist": "Alex Chen",
        "email": "alex.chen@ourcompany.com",
        "expertise": ["API Integration", "System Architecture", "Performance Issues"],
        "response_time": "2-4 hours",
    },
    "Billing": {
        "specialist": "Maria Rodriguez",
        "email": "maria.rodriguez@ourcompany.com",
        "expertise": ["Payment Processing", "Refunds", "Subscription Management"],
        "response_time": "1-2 hours",
    },
    "Account": {
        "specialist": "James Wilson",
        "email": "james.wilson@ourcompany.com",
        "expertise": ["Account Management", "Security", "Access Issues"],
        "response_time": "1-3 hours",
    },
    "General": {
        "specialist": "Sarah Thompson",
        "email": "sarah.thompson@ourcompany.com",
        "expertise": ["General Inquiries", "Feature Requests", "Feedback"],
        "response_time": "4-8 hours",
    },
    "Urgent": {
        "specialist": "Emergency Team",
        "email": "emergency@ourcompany.com",
        "expertise": ["Critical Issues", "System Outages", "Security Incidents"],
        "response_time": "15-30 minutes",
    },
}


def load_customer_data(csv_path: str) -> Dict[str, Dict[str, Any]]:
    customers: Dict[str, Dict[str, Any]] = {}
    if not os.path.exists(csv_path):
        return customers
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cust_id = (row.get("customer_id") or "").strip()
            if not cust_id:
                continue
            customers[cust_id] = {
                "customer_id": cust_id,
                "name": row.get("name", ""),
                "email": row.get("email", ""),
                "plan": row.get("plan", ""),
                "subscription_status": row.get("subscription_status", ""),
                "last_login": row.get("last_login", ""),
                "account_age_days": int(row.get("account_age_days", 0) or 0),
                "previous_issues": int(row.get("previous_issues", 0) or 0),
            }
    return customers


def load_demo_customers() -> Dict[str, Dict[str, Any]]:
    return {
        "CUST001": {
            "customer_id": "CUST001",
            "name": "김민준",
            "email": "kim.minjun@email.com",
            "plan": "Premium",
            "subscription_status": "active",
            "last_login": "2024-01-15",
            "account_age_days": 365,
            "previous_issues": 2,
        }
    }