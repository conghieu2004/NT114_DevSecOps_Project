#!/usr/bin/env python3
"""Test password verification for debugging"""

from flask_bcrypt import Bcrypt
from flask import Flask

app = Flask(__name__)
bcrypt = Bcrypt(app)

# Password hash from database (PostgreSQL escaped format)
# Raw: \b\2\K1p/a0dL3.I0/Z0ZUvV5uTxcO.3bqPCOCLYM5bQjhfjKcE3pTz0G
db_password_escaped = r"\b\2\K1p/a0dL3.I0/Z0ZUvV5uTxcO.3bqPCOCLYM5bQjhfjKcE3pTz0G"

# Try to convert back to proper bcrypt format
# bcrypt hashes should start with $2b$ not \b\2\K
db_password_fixed = "$2b$12" + db_password_escaped.split(r"\K1", 1)[1] if r"\K1" in db_password_escaped else db_password_escaped

test_password = "123456789"

print(f"Original DB password: {db_password_escaped}")
print(f"Length: {len(db_password_escaped)}")
print(f"\nAttempting to fix format...")
print(f"Fixed password: {db_password_fixed}")
print(f"Length: {len(db_password_fixed)}")

# Test 1: Try with escaped version
print("\n=== Test 1: Using escaped version ===")
try:
    result = bcrypt.check_password_hash(db_password_escaped, test_password)
    print(f"Result: {result}")
except Exception as e:
    print(f"Error: {e}")

# Test 2: Try with fixed version
print("\n=== Test 2: Using fixed bcrypt format ===")
try:
    result = bcrypt.check_password_hash(db_password_fixed, test_password)
    print(f"Result: {result}")
except Exception as e:
    print(f"Error: {e}")

# Test 3: Generate a new hash for comparison
print("\n=== Test 3: Generate new hash for '123456789' ===")
new_hash = bcrypt.generate_password_hash(test_password, 12).decode()
print(f"New hash: {new_hash}")
print(f"Length: {len(new_hash)}")

# Test 4: Verify the new hash works
print("\n=== Test 4: Verify new hash ===")
try:
    result = bcrypt.check_password_hash(new_hash, test_password)
    print(f"Result: {result}")
except Exception as e:
    print(f"Error: {e}")
