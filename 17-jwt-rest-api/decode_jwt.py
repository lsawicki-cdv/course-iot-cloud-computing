#!/usr/bin/env python3
"""
JWT Token Decoder

This script decodes and displays the contents of a JWT token.
Useful for understanding what information is stored in the token.
"""

import jwt
import json
import sys
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'dev-secret-key-change-in-production')


def decode_token(token_string, verify=True):
    """
    Decode a JWT token and display its contents.

    Args:
        token_string: The JWT token to decode
        verify: Whether to verify the signature (requires secret key)
    """
    print("=" * 70)
    print("JWT Token Decoder")
    print("=" * 70)
    print()

    # Display the raw token (truncated)
    print("Raw Token (first 80 chars):")
    print(f"  {token_string[:80]}...")
    print()

    # Split token into parts
    parts = token_string.split('.')
    if len(parts) != 3:
        print("❌ Error: Invalid JWT format. Expected 3 parts separated by dots.")
        return

    print(f"Token Structure:")
    print(f"  Header:    {parts[0][:40]}...")
    print(f"  Payload:   {parts[1][:40]}...")
    print(f"  Signature: {parts[2][:40]}...")
    print()

    # Decode without verification first (to see contents even if signature is invalid)
    try:
        print("-" * 70)
        print("HEADER (Algorithm and Type)")
        print("-" * 70)
        header = jwt.get_unverified_header(token_string)
        print(json.dumps(header, indent=2))
        print()

        print("-" * 70)
        print("PAYLOAD (Claims)")
        print("-" * 70)
        payload = jwt.decode(token_string, options={"verify_signature": False})
        print(json.dumps(payload, indent=2))
        print()

        # Parse common fields
        if 'exp' in payload:
            exp_timestamp = payload['exp']
            exp_datetime = datetime.fromtimestamp(exp_timestamp)
            now = datetime.now()

            print("Token Expiration:")
            print(f"  Expires at: {exp_datetime.strftime('%Y-%m-%d %H:%M:%S')}")

            if now > exp_datetime:
                print(f"  ⚠ Token has EXPIRED")
            else:
                remaining = exp_datetime - now
                print(f"  ✓ Token is valid for {remaining.total_seconds():.0f} more seconds")
            print()

        if 'iat' in payload:
            iat_timestamp = payload['iat']
            iat_datetime = datetime.fromtimestamp(iat_timestamp)
            print(f"Token Issued At:")
            print(f"  {iat_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
            print()

        if 'user_id' in payload:
            print(f"User Information:")
            print(f"  User ID: {payload.get('user_id')}")
            print(f"  Username: {payload.get('username', 'N/A')}")
            print()

    except jwt.DecodeError as e:
        print(f"❌ Error decoding token: {e}")
        return

    # Now verify signature if requested
    if verify:
        print("-" * 70)
        print("SIGNATURE VERIFICATION")
        print("-" * 70)

        try:
            verified_payload = jwt.decode(
                token_string,
                SECRET_KEY,
                algorithms=['HS256']
            )
            print("✓ Signature is VALID")
            print(f"  Token was signed with the correct secret key")
            print(f"  Token has not been tampered with")
        except jwt.ExpiredSignatureError:
            print("⚠ Token signature is valid but token has EXPIRED")
        except jwt.InvalidSignatureError:
            print("❌ INVALID Signature")
            print("  Token may have been tampered with")
            print("  OR wrong secret key is being used")
        except jwt.InvalidTokenError as e:
            print(f"❌ Invalid token: {e}")

        print()

    print("=" * 70)


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python decode_jwt.py <jwt_token>")
        print()
        print("Example:")
        print("  python decode_jwt.py eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
        print()
        print("To get a token:")
        print("  1. Run the API server: python app.py")
        print("  2. Login: curl -X POST http://localhost:5000/api/login \\")
        print("             -H 'Content-Type: application/json' \\")
        print("             -d '{\"username\": \"testuser\", \"password\": \"testpass\"}'")
        print("  3. Copy the token from the response")
        sys.exit(1)

    token = sys.argv[1]

    # Remove "Bearer " prefix if present
    if token.startswith("Bearer "):
        token = token[7:]

    decode_token(token, verify=True)


if __name__ == "__main__":
    main()
