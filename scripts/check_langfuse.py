#!/usr/bin/env python3
"""
Script para verificar conexão com Langfuse.
Usado pelo Makefile: make langfuse-check
"""
import os
import sys

def check_langfuse():
    host = os.getenv('LANGFUSE_HOST', 'NOT SET')
    public_key = os.getenv('LANGFUSE_PUBLIC_KEY', '')
    secret_key = os.getenv('LANGFUSE_SECRET_KEY', '')

    pk_display = public_key[:15] + '...' if public_key else 'NOT SET'
    sk_display = secret_key[:15] + '...' if secret_key else 'NOT SET'

    print(f"Host:       {host}")
    print(f"Public Key: {pk_display}")
    print(f"Secret Key: {sk_display}")

    if not public_key or not secret_key:
        print("❌ Langfuse keys not configured")
        return False

    try:
        from langfuse import Langfuse
        lf = Langfuse()
        lf.auth_check()
        print("✅ Langfuse connection OK")
        return True
    except ImportError:
        print("❌ Langfuse package not installed")
        return False
    except Exception as e:
        print(f"❌ Langfuse error: {e}")
        return False

if __name__ == "__main__":
    success = check_langfuse()
    sys.exit(0 if success else 1)
