"""
Shared utility functions used across PrepAIEngine.
"""
import hashlib
import json
import logging
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ─── Identifiers ──────────────────────────────────────────────────────────────

def generate_session_id() -> str:
    return str(uuid.uuid4())


def hash_text(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


# ─── Text Processing ──────────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def truncate_text(text: str, max_length: int = 3000) -> str:
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def safe_json_loads(raw: str) -> Optional[Dict]:
    """
    Try to parse JSON from a string that may contain surrounding prose.
    Returns the first valid JSON object found, or None.
    """
    if not raw:
        return None
    # Direct parse first
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        pass
    # Extract first {...} block
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


# ─── Normalization ────────────────────────────────────────────────────────────

_COMPANY_MAP: Dict[str, str] = {
    "google": "Google",
    "alphabet": "Google",
    "amazon": "Amazon",
    "aws": "Amazon",
    "meta": "Meta",
    "facebook": "Meta",
    "apple": "Apple",
    "microsoft": "Microsoft",
    "msft": "Microsoft",
    "netflix": "Netflix",
    "uber": "Uber",
    "lyft": "Lyft",
    "airbnb": "Airbnb",
    "twitter": "X (Twitter)",
    "x corp": "X (Twitter)",
    "salesforce": "Salesforce",
    "oracle": "Oracle",
    "ibm": "IBM",
    "linkedin": "LinkedIn",
    "snapchat": "Snap",
    "snap": "Snap",
    "stripe": "Stripe",
    "coinbase": "Coinbase",
    "dropbox": "Dropbox",
    "slack": "Slack",
    "zoom": "Zoom",
    "nvidia": "NVIDIA",
    "adobe": "Adobe",
    "palantir": "Palantir",
    "tiktok": "TikTok",
    "bytedance": "ByteDance",
    "two sigma": "Two Sigma",
    "jane street": "Jane Street",
    "citadel": "Citadel",
    "de shaw": "D. E. Shaw",
    "goldman": "Goldman Sachs",
    "jpmorgan": "JPMorgan",
    "jp morgan": "JPMorgan",
    "bloomberg": "Bloomberg",
    "databricks": "Databricks",
    "snowflake": "Snowflake",
    "doordash": "DoorDash",
    "robinhood": "Robinhood",
    "figma": "Figma",
    "notion": "Notion",
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "waymo": "Waymo",
    "tesla": "Tesla",
    "intel": "Intel",
    "qualcomm": "Qualcomm",
    "walmart": "Walmart",
    "walmart labs": "Walmart",
    "target": "Target",
    "optum": "Optum",
    "unitedhealth": "UnitedHealth",
    "visa": "Visa",
    "mastercard": "Mastercard",
    "american express": "American Express",
    "amex": "American Express",
    "capital one": "Capital One",
    "paypal": "PayPal",
    "ebay": "eBay",
    "expedia": "Expedia",
    "booking": "Booking.com",
    "yelp": "Yelp",
    "pinterest": "Pinterest",
    "reddit": "Reddit",
    "quora": "Quora",
    "medium": "Medium",
    "atlassian": "Atlassian",
    "jira": "Atlassian",
    "confluent": "Confluent",
    "elastic": "Elastic",
    "mongodb": "MongoDB",
    "cockroach": "CockroachDB",
    "cockroachdb": "CockroachDB",
    "vercel": "Vercel",
    "netlify": "Netlify",
    "cloudflare": "Cloudflare",
    "hashicorp": "HashiCorp",
    "datadog": "Datadog",
    "splunk": "Splunk",
    "pagerduty": "PagerDuty",
    "twilio": "Twilio",
    "sendgrid": "Twilio",
    "okta": "Okta",
    "auth0": "Okta",
    "crowdstrike": "CrowdStrike",
    "palo alto": "Palo Alto Networks",
    "fortinet": "Fortinet",
    "servicenow": "ServiceNow",
    "workday": "Workday",
    "sap": "SAP",
    "oracle": "Oracle",
    "hpe": "HPE",
    "hp": "HP",
    "dell": "Dell",
    "cisco": "Cisco",
    "juniper": "Juniper Networks",
    "vmware": "VMware",
    "broadcom": "Broadcom",
    "amd": "AMD",
    "arm": "ARM",
    "samsung": "Samsung",
    "sony": "Sony",
    "lg": "LG",
    "huawei": "Huawei",
    "tencent": "Tencent",
    "alibaba": "Alibaba",
    "baidu": "Baidu",
    "infosys": "Infosys",
    "wipro": "Wipro",
    "tcs": "TCS",
    "tata consultancy": "TCS",
    "accenture": "Accenture",
    "deloitte": "Deloitte",
    "mckinsey": "McKinsey",
    "thoughtworks": "ThoughtWorks",
    "squareup": "Square",
    "block": "Block",
    "square": "Square",
    "cash app": "Block",
    "roblox": "Roblox",
    "epic games": "Epic Games",
    "unity": "Unity",
    "activision": "Activision",
    "blizzard": "Blizzard",
    "ea": "Electronic Arts",
    "electronic arts": "Electronic Arts",
    "hulu": "Hulu",
    "disney": "Disney",
    "warner": "Warner Bros",
    "nbc": "NBCUniversal",
    "comcast": "Comcast",
    "att": "AT&T",
    "at&t": "AT&T",
    "verizon": "Verizon",
    "t-mobile": "T-Mobile",
    "spacex": "SpaceX",
    "rivian": "Rivian",
    "lucid": "Lucid Motors",
    "cruise": "Cruise",
    "aurora": "Aurora",
    "nuro": "Nuro",
    "scale ai": "Scale AI",
    "scaleai": "Scale AI",
    "cohere": "Cohere",
    "mistral": "Mistral AI",
    "hugging face": "Hugging Face",
    "stability": "Stability AI",
    "inflection": "Inflection AI",
    "cerebras": "Cerebras",
    "groq": "Groq",
    "anduril": "Anduril",
    "faire": "Faire",
    "instacart": "Instacart",
    "grubhub": "Grubhub",
    "doordash": "DoorDash",
    "postmates": "Postmates",
    "chime": "Chime",
    "plaid": "Plaid",
    "brex": "Brex",
    "affirm": "Affirm",
    "klarna": "Klarna",
    "nubank": "Nubank",
    "wealthfront": "Wealthfront",
    "betterment": "Betterment",
    "zendesk": "Zendesk",
    "hubspot": "HubSpot",
    "intercom": "Intercom",
    "asana": "Asana",
    "monday": "Monday.com",
    "clickup": "ClickUp",
    "linear": "Linear",
    "airtable": "Airtable",
    "smartsheet": "Smartsheet",
}

_ROLE_MAP: Dict[str, str] = {
    "swe": "Software Engineer",
    "software engineer": "Software Engineer",
    "software developer": "Software Engineer",
    "sde": "Software Engineer",
    "sde1": "Software Engineer I",
    "sde-1": "Software Engineer I",
    "sde2": "Software Engineer II",
    "sde-2": "Software Engineer II",
    "sde3": "Software Engineer III",
    "l3": "Software Engineer L3",
    "l4": "Software Engineer L4",
    "l5": "Software Engineer L5",
    "l6": "Software Engineer L6",
    "e3": "Software Engineer E3",
    "e4": "Software Engineer E4",
    "e5": "Software Engineer E5",
    "e6": "Software Engineer E6",
    "mle": "Machine Learning Engineer",
    "ml engineer": "Machine Learning Engineer",
    "machine learning engineer": "Machine Learning Engineer",
    "ds": "Data Scientist",
    "data scientist": "Data Scientist",
    "da": "Data Analyst",
    "data analyst": "Data Analyst",
    "pm": "Product Manager",
    "product manager": "Product Manager",
    "apm": "Associate Product Manager",
    "tpm": "Technical Program Manager",
    "em": "Engineering Manager",
    "engineering manager": "Engineering Manager",
    "sre": "Site Reliability Engineer",
    "devops": "DevOps Engineer",
    "backend engineer": "Backend Engineer",
    "frontend engineer": "Frontend Engineer",
    "fullstack": "Full Stack Engineer",
    "full stack engineer": "Full Stack Engineer",
    "security engineer": "Security Engineer",
    "research scientist": "Research Scientist",
    "research engineer": "Research Engineer",
}


def normalize_company(name: str) -> str:
    if not name:
        return ""
    name = clean_text(name)
    lower = name.lower()
    for key, canonical in _COMPANY_MAP.items():
        if key in lower:
            return canonical
    return name.title()


def normalize_role(role: str) -> str:
    if not role:
        return ""
    role = clean_text(role)
    lower = role.lower()
    if lower in _ROLE_MAP:
        return _ROLE_MAP[lower]
    for key, canonical in _ROLE_MAP.items():
        if key in lower:
            return canonical
    return role.title()


# ─── Data Utilities ───────────────────────────────────────────────────────────

def extract_company_from_text(text: str) -> str:
    """
    Regex-based fallback: scan raw text for any known company name.
    Returns the canonical name if found, empty string otherwise.
    """
    if not text:
        return ""
    lower = text.lower()
    # Sort by length descending so "jp morgan" matches before "morgan"
    for key in sorted(_COMPANY_MAP.keys(), key=len, reverse=True):
        if re.search(r'\b' + re.escape(key) + r'\b', lower):
            return _COMPANY_MAP[key]
    return ""


def is_useful_record(data: dict) -> bool:
    """
    Returns False for records that carry no actionable interview signal:
    no company, no role, no topics, no questions, and no rounds.
    These are noise posts (memes, general rants, etc.).
    """
    has_company   = bool(data.get("company"))
    has_role      = bool(data.get("role"))
    has_topics    = bool(data.get("topics"))
    has_questions = bool(data.get("questions"))
    has_rounds    = bool(data.get("rounds"))
    return any([has_company, has_role, has_topics, has_questions, has_rounds])


def deduplicate(items: List[str]) -> List[str]:
    seen: set = set()
    result: List[str] = []
    for item in items:
        key = item.lower().strip()
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def flatten(nested: List[Any]) -> List[Any]:
    result: List[Any] = []
    for item in nested:
        if isinstance(item, list):
            result.extend(flatten(item))
        else:
            result.append(item)
    return result


def format_timestamp(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def chunk_list(lst: List[Any], size: int) -> List[List[Any]]:
    return [lst[i : i + size] for i in range(0, len(lst), size)]
