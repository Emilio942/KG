
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import hashlib
import hmac

class EnterpriseEncryption:
    """
    Enterprise-grade encryption utilities for KG-System
    AES-256 encryption for sensitive data
    """
    
    def __init__(self, master_key: str):
        self.master_key = master_key.encode()
        self.fernet_key = self._derive_fernet_key()
        self.cipher_suite = Fernet(self.fernet_key)
    
    def _derive_fernet_key(self) -> bytes:
        """Derive Fernet key from master key"""
        salt = b'kg_system_enterprise_salt_2025'
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.master_key))
        return key
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data (PII, credentials, etc.)"""
        encrypted_data = self.cipher_suite.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted_data).decode()
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
        decrypted_data = self.cipher_suite.decrypt(encrypted_bytes)
        return decrypted_data.decode()
    
    def encrypt_tenant_data(self, tenant_id: str, data: dict) -> str:
        """Encrypt tenant-specific data with tenant-derived key"""
        tenant_salt = f"tenant_{tenant_id}_salt".encode()
        tenant_kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=tenant_salt,
            iterations=100000,
        )
        tenant_key = base64.urlsafe_b64encode(tenant_kdf.derive(self.master_key))
        tenant_cipher = Fernet(tenant_key)
        
        json_data = json.dumps(data)
        encrypted_data = tenant_cipher.encrypt(json_data.encode())
        return base64.urlsafe_b64encode(encrypted_data).decode()
    
    def hash_for_audit(self, data: str, tenant_id: str) -> str:
        """Create audit-safe hash"""
        combined = f"{data}:{tenant_id}:kg_system_enterprise"
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def verify_data_integrity(self, data: str, expected_hash: str, tenant_id: str) -> bool:
        """Verify data integrity using hash"""
        calculated_hash = self.hash_for_audit(data, tenant_id)
        return hmac.compare_digest(calculated_hash, expected_hash)
