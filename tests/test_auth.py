"""
Unit tests for src/auth.py
Validates password hashing, user registration, authentication flow, and RBAC personas.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from auth import (
    hash_password,
    authenticate_user,
    register_user,
    get_demo_accounts,
    ROLES,
)


def test_password_hashing():
    pw1 = "testpassword123"
    hash1 = hash_password(pw1)
    assert len(hash1) == 64  # SHA-256 is 64 hex characters
    assert hash1 == hash_password(pw1)
    assert hash1 != hash_password("differentpassword")


def test_demo_accounts_authentication():
    demo_users = get_demo_accounts()
    assert len(demo_users) >= 3

    # Test login for Commodities Trader (Infotact Core Desk)
    trader = demo_users["Commodities Trader (Infotact Core Desk)"]
    t_ok, t_user, _ = authenticate_user(trader["email"], trader["password"])
    assert t_ok is True
    assert t_user["role"] == "Commodities Trader"

    # Test login for Jahnavi (Agronomist)
    agro = demo_users["Agronomist (Field Researcher)"]
    success, user_info, msg = authenticate_user(agro["email"], agro["password"])
    assert success is True
    assert user_info["role"] == "Agronomist"
    assert "Jahnavi" in user_info["name"]

    # Test login failure with wrong password
    bad_login, bad_info, bad_msg = authenticate_user(agro["email"], "wrong_password_xyz")
    assert bad_login is False
    assert bad_info is None
    assert "Incorrect password" in bad_msg


def test_user_registration():
    new_email = "mentor_eval@infotact.in"
    new_pass = "mentorPass2026"
    success, msg = register_user(
        name="Infotact Mentor",
        email=new_email,
        password=new_pass,
        role="Farm Manager",
        organization="Infotact Academic Evaluation",
    )
    assert success is True or "already exists" in msg

    # Authenticate newly created account
    auth_ok, auth_user, _ = authenticate_user(new_email, new_pass)
    assert auth_ok is True
    assert auth_user["name"] == "Infotact Mentor"
    assert auth_user["role"] == "Farm Manager"


def test_role_definitions():
    assert "Agronomist" in ROLES
    assert "Farm Manager" in ROLES
    assert "Supply Chain Analyst" in ROLES


if __name__ == "__main__":
    test_password_hashing()
    test_demo_accounts_authentication()
    test_user_registration()
    test_role_definitions()
    print("All auth unit tests passed successfully!")
