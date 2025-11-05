"""
Authentication module with intentional security vulnerabilities for demo purposes.
This code demonstrates common security issues that AI code review can detect.
"""

import hashlib
import os


def login(username, password):
    """
    Authenticate user - contains SQL injection vulnerability.
    
    ⚠️ SECURITY ISSUE: Direct string interpolation in SQL query
    """
    query = f"SELECT * FROM users WHERE name='{username}' AND pass='{password}'"
    # SQL injection vulnerability - attacker can inject malicious SQL
    return execute_query(query)


def hash_password(password):
    """
    Hash password using MD5 - weak and deprecated.
    
    ⚠️ SECURITY ISSUE: MD5 is cryptographically broken
    """
    return hashlib.md5(password.encode()).hexdigest()
    # Should use bcrypt, argon2, or PBKDF2 instead


def store_api_key(api_key):
    """
    Store API key in plain text.
    
    ⚠️ SECURITY ISSUE: Sensitive data stored in plain text
    """
    with open("api_keys.txt", "w") as f:
        f.write(api_key)
    # Should use environment variables or secure key management


def get_secret_key():
    """
    Hardcoded secret key.
    
    ⚠️ SECURITY ISSUE: Hardcoded secret in source code
    """
    return "my-secret-key-12345"
    # Should use environment variables or secure configuration
