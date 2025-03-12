"""
Utility script to generate a development JWT token.
"""
import sys
import os
import jwt
from datetime import datetime, timedelta

# Add the parent directory to the path so we can import from the app
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.app.config import settings

def generate_dev_token(user_id="dev_user", expires_days=30):
    """
    Generate a development JWT token.
    
    Args:
        user_id: The user ID to encode in the token
        expires_days: The number of days until the token expires
        
    Returns:
        str: The encoded JWT token
    """
    # Create token data
    data = {
        "sub": user_id,
        "name": "Development User",
        "email": "dev@example.com",
        "roles": ["user", "admin"],
        "exp": datetime.utcnow() + timedelta(days=expires_days)
    }
    
    # Encode token
    token = jwt.encode(
        data,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return token

if __name__ == "__main__":
    # Generate token
    token = generate_dev_token()
    
    # Print token
    print("\nDevelopment JWT Token:")
    print(token)
    print("\nThis token will be valid for 30 days.")
    print("Add this token to your frontend WebSocket context for development purposes.")