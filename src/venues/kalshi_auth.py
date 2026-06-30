"""
kalshi_auth.py
--------------
Generates the three authentication headers required by every Kalshi API request.

Kalshi uses RSA-PSS signature authentication. Every request must include:
    KALSHI-ACCESS-KEY       : your API key ID (from .env)
    KALSHI-ACCESS-TIMESTAMP : current UTC time in milliseconds (as string)
    KALSHI-ACCESS-SIGNATURE : base64-encoded RSA-PSS signature of the message

The message that gets signed is constructed as:
    timestamp + http_method + path

Example for a GET to /trade-api/v2/markets:
    "1719619200000GET/trade-api/v2/markets"

The signature is produced by:
    1. Hashing the message with SHA-256
    2. Signing the hash with your RSA private key using PSS padding
    3. Base64-encoding the raw signature bytes

Usage:
    from src.venues.kalshi_auth import build_headers
    headers = build_headers(method="GET", path="/trade-api/v2/markets")
"""

import os
import time
import base64

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from dotenv import load_dotenv

load_dotenv()


def _load_private_key():
    """
    Loads the RSA private key from the path specified in .env.

    Returns a cryptography RSAPrivateKey object.
    Raises FileNotFoundError if the path is wrong or the file is missing.
    """
    key_path = os.getenv("KALSHI_PRIVATE_KEY_PATH")

    if not key_path:
        raise EnvironmentError(
            "KALSHI_PRIVATE_KEY_PATH is not set in your .env file. "
            "It should point to your kalshi_private.pem file."
        )

    if not os.path.exists(key_path):
        raise FileNotFoundError(
            f"Private key not found at: {key_path}. "
            "Make sure kalshi_private.pem is in your project root."
        )

    with open(key_path, "rb") as f:
        private_key = serialization.load_pem_private_key(
            f.read(),
            password=None,           # we generated the key without a passphrase
            backend=default_backend()
        )

    return private_key


def _get_timestamp_ms() -> str:
    """
    Returns current UTC time in milliseconds as a string.
    Kalshi requires the timestamp in this exact format.

    Example output: "1719619200000"
    """
    return str(round(time.time() * 1000))


def _sign_message(private_key, message: str) -> str:
    """
    Signs a message string using RSA-PSS with SHA-256.

    Steps:
        1. Encode the message string to bytes (UTF-8)
        2. Sign using RSA-PSS padding with SHA-256 as both the
           hash algorithm and the MGF1 mask generation hash
        3. Base64-encode the raw signature bytes
        4. Return as a UTF-8 string

    Args:
        private_key : RSAPrivateKey object from _load_private_key()
        message     : the string to sign (timestamp + method + path)

    Returns:
        Base64-encoded signature string
    """
    message_bytes = message.encode("utf-8")

    signature_bytes = private_key.sign(
        message_bytes,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=32
        ),
        hashes.SHA256()
    )

    return base64.b64encode(signature_bytes).decode("utf-8")


def build_headers(method: str, path: str) -> dict:
    """
    Builds the three authentication headers required for every Kalshi request.

    Args:
        method : HTTP method in uppercase — "GET" or "POST"
        path   : API path including /trade-api/v2 prefix
                 e.g. "/trade-api/v2/markets"
                 Do NOT include query parameters in the path here.

    Returns:
        dict with keys:
            KALSHI-ACCESS-KEY
            KALSHI-ACCESS-TIMESTAMP
            KALSHI-ACCESS-SIGNATURE

    Example:
        headers = build_headers("GET", "/trade-api/v2/markets")
        response = requests.get(url, headers=headers, params={...})
    """
    api_key = os.getenv("KALSHI_API_KEY")

    if not api_key:
        raise EnvironmentError(
            "KALSHI_API_KEY is not set in your .env file."
        )

    timestamp = _get_timestamp_ms()

    # The message Kalshi expects us to sign:
    # timestamp (ms) + HTTP method (uppercase) + full path (no query string)
    message = timestamp + method.upper() + path

    private_key = _load_private_key()
    signature   = _sign_message(private_key, message)

    return {
        "KALSHI-ACCESS-KEY":       api_key,
        "KALSHI-ACCESS-TIMESTAMP": timestamp,
        "KALSHI-ACCESS-SIGNATURE": signature,
        "Content-Type":            "application/json"
    }


if __name__ == "__main__":
    """
    Quick sanity check — run this file directly to verify your keys
    and .env are configured correctly before writing kalshi.py.

    Run with:
        python src/venues/kalshi_auth.py

    Expected output:
        Private key loaded successfully.
        Headers built successfully.
        KALSHI-ACCESS-KEY      : abc123...
        KALSHI-ACCESS-TIMESTAMP: 1719619200000
        KALSHI-ACCESS-SIGNATURE: <long base64 string>
    """
    print("Testing kalshi_auth setup...\n")

    try:
        key = _load_private_key()
        print("Private key loaded successfully.")
    except Exception as e:
        print(f"ERROR loading private key: {e}")
        exit(1)

    try:
        headers = build_headers("GET", "/trade-api/v2/markets")
        print("Headers built successfully.\n")
        print(f"KALSHI-ACCESS-KEY      : {headers['KALSHI-ACCESS-KEY']}")
        print(f"KALSHI-ACCESS-TIMESTAMP: {headers['KALSHI-ACCESS-TIMESTAMP']}")
        print(f"KALSHI-ACCESS-SIGNATURE: {headers['KALSHI-ACCESS-SIGNATURE'][:40]}...")
    except Exception as e:
        print(f"ERROR building headers: {e}")
        exit(1)