"""Script to reset user password in database"""
import sys
import os

# Add app directory to path
sys.path.insert(0, '/app')

from app import create_app, db
from app.models import User
from flask_bcrypt import Bcrypt

# Create app
app = create_app()
bcrypt = Bcrypt(app)

with app.app_context():
    # Find user
    email = 'phuocvanho2004@gmail.com'
    user = User.query.filter_by(email=email).first()

    if user:
        print(f"Found user: {user.username} ({user.email})")
        print(f"Current password hash: {user.password}")

        # Set new password
        new_password = '123456789'
        user.password = bcrypt.generate_password_hash(new_password, 12).decode()

        # Save to database
        db.session.commit()

        print(f"✓ Password updated successfully!")
        print(f"New password hash: {user.password}")

        # Verify the password works
        is_valid = bcrypt.check_password_hash(user.password, new_password)
        print(f"✓ Password verification: {is_valid}")
    else:
        print(f"✗ User not found: {email}")
