"""Encryption utilities for sensitive data."""

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64
import os

from app.core.config import settings


def get_encryption_key() -> bytes:
    """Generate or retrieve encryption key from secret.

    Returns:
        Encryption key bytes.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"fixed_salt_change_in_production",
        iterations=100000,
        backend=default_backend(),
    )
    key = base64.urlsafe_b64encode(
        kdf.derive(settings.secret_key.encode())
    )
    return key


def encrypt_data(data: str) -> str:
    """Encrypt sensitive data.

    Args:
        data: Plain text data to encrypt.

    Returns:
        Encrypted data as base64 string.
    """
    f = Fernet(get_encryption_key())
    encrypted = f.encrypt(data.encode())
    return base64.b64encode(encrypted).decode()


def decrypt_data(encrypted_data: str) -> str:
    """Decrypt sensitive data.

    Args:
        encrypted_data: Encrypted data as base64 string.

    Returns:
        Decrypted plain text data.
    """
    f = Fernet(get_encryption_key())
    decoded = base64.b64decode(encrypted_data.encode())
    decrypted = f.decrypt(decoded)
    return decrypted.decode()

