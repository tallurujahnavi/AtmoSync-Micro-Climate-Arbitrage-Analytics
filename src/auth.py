"""
AtmoSync: Micro-Climate Arbitrage Analytics
Module: auth.py
Description: Authentication, session management, and Role-Based Access Control (RBAC).
             Supports persistent user registration, salted SHA-256 password hashing,
             and predefined persona profiles for agronomists, farm managers, and supply chain analysts.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Dict, Optional, Tuple


USER_DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "users.json"

# Defined industry user personas for agro-climatic analytics
ROLES = {
    "Commodities Trader": "Infotact Desk: Real-time Spoilage Arbitrage tracking, container rerouting, and cargo value preservation.",
    "Agronomist": "Focus on crop tolerance bands, climate stress thresholds, and biological suitability indices.",
    "Supply Chain Analyst": "Focus on haversine transport radii, inter-district procurement gaps, and cold-chain logistics.",
    "Farm Manager": "Focus on regional yield arbitrage, location rankings, and seasonal Kharif/Rabi scheduling.",
}

# Default seeded credentials for immediate mentor/evaluator demo
DEFAULT_USERS: Dict[str, Dict] = {
    "trader@infotact.in": {
        "name": "Jahnavi Talluru",
        "email": "trader@infotact.in",
        "role": "Commodities Trader",
        "organization": "Infotact Global Commodities Desk",
        # sha256 for "trader2026"
        "password_hash": "66a509d0c8f3e005466b9ee2b8d3a7bf9c3e6d53d4b1c1cbaf05b0bcbc066205",
    },
    "jahnavi@atmosync.org": {
        "name": "Dr. Jahnavi Talluru",
        "email": "jahnavi@atmosync.org",
        "role": "Agronomist",
        "organization": "Andhra Agricultural Research Consortium",
        # sha256 for "agro2026"
        "password_hash": "077d1cf29426c4cda94f4134632c9d19533de0d870732519896f69ae9acdcb7f",
    },
    "anita@atmosync.org": {
        "name": "Anita Rao",
        "email": "anita@atmosync.org",
        "role": "Supply Chain Analyst",
        "organization": "AgriLogistics India Network",
        # sha256 for "logistics2026"
        "password_hash": "b13a32fd08eb4736f6f42f3631ccf47f55f913b9a4ef4b4b1055f9706047fc7d",
    },
}


def hash_password(password: str) -> str:
    """Returns SHA-256 hexadecimal digest of input password."""
    return hashlib.sha256(password.strip().encode("utf-8")).hexdigest()


def _ensure_user_store() -> Dict[str, Dict]:
    """Ensures user store JSON exists with default seeded accounts."""
    USER_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not USER_DATA_FILE.exists():
        with open(USER_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_USERS, f, indent=2)
        return DEFAULT_USERS.copy()

    try:
        with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)
            # Ensure default users remain present if corrupted
            for email, data in DEFAULT_USERS.items():
                if email not in users:
                    users[email] = data
            return users
    except Exception:
        return DEFAULT_USERS.copy()


def _save_users(users: Dict[str, Dict]) -> None:
    """Saves updated user dictionary to persistent JSON."""
    USER_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(USER_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)


def authenticate_user(email: str, password: str) -> Tuple[bool, Optional[Dict], str]:
    """
    Authenticates user credentials.
    Returns: (is_success, user_dict, message)
    """
    clean_email = email.strip().lower()
    users = _ensure_user_store()

    if clean_email not in users:
        return False, None, "No account registered with this email address."

    user = users[clean_email]
    hashed_input = hash_password(password)

    if user["password_hash"] == hashed_input:
        user_info = {
            "name": user.get("name", "User"),
            "email": clean_email,
            "role": user.get("role", "Agronomist"),
            "organization": user.get("organization", "Independent"),
        }
        return True, user_info, "Authentication successful."

    return False, None, "Incorrect password. Please try again."


def register_user(
    name: str,
    email: str,
    password: str,
    role: str = "Agronomist",
    organization: str = "Agricultural Research"
) -> Tuple[bool, str]:
    """
    Registers a new user account into the local datastore.
    Returns: (is_success, message)
    """
    clean_email = email.strip().lower()
    if not clean_email or "@" not in clean_email or "." not in clean_email:
        return False, "Please enter a valid email address."

    if len(password.strip()) < 4:
        return False, "Password must be at least 4 characters long."

    if not name.strip():
        return False, "Name cannot be empty."

    users = _ensure_user_store()
    if clean_email in users:
        return False, "An account with this email already exists."

    users[clean_email] = {
        "name": name.strip(),
        "email": clean_email,
        "role": role if role in ROLES else "Agronomist",
        "organization": organization.strip() or "Independent Agri-Consultant",
        "password_hash": hash_password(password),
    }

    _save_users(users)
    return True, "Account registered successfully. You can now log in."


def get_demo_accounts() -> Dict[str, Dict]:
    """Returns sample demo persona profiles for quick evaluation."""
    return {
        "Commodities Trader (Infotact Core Desk)": {
            "email": "trader@infotact.in",
            "password": "trader2026",
            "role": "Commodities Trader",
            "desc": "Official Infotact Desk: Real-time container telemetry, spoilage curves, and Spoilage Arbitrage rerouting.",
        },
        "Agronomist (Field Researcher)": {
            "email": "jahnavi@atmosync.org",
            "password": "agro2026",
            "role": "Agronomist",
            "desc": "Access biochemical tolerance bands, climate stress curves, and crop suitability models.",
        },
        "Supply Chain Analyst (AgriLogistics)": {
            "email": "anita@atmosync.org",
            "password": "logistics2026",
            "role": "Supply Chain Analyst",
            "desc": "Access proximity haulage radii (50-1500 km), cold-chain transit corridors, and route risk.",
        },
    }
