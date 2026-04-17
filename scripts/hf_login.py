#!/usr/bin/env python3
"""
Simple script to login to Hugging Face
"""

from huggingface_hub import login
import sys

print("\n" + "="*70)
print("         HUGGING FACE LOGIN")
print("="*70)
print("\n🔑 Please paste your Hugging Face token below.")
print("   (Get it from: https://huggingface.co/settings/tokens)")
print("\n⚠️  Make sure you've accepted the Gemma license at:")
print("   https://huggingface.co/google/gemma-2b")
print("\n" + "-"*70)

token = input("\nToken: ").strip()

if not token:
    print("\n❌ No token provided. Exiting.")
    sys.exit(1)

try:
    login(token=token, add_to_git_credential=False)
    print("\n✅ Successfully logged in to Hugging Face!")
    print("   You can now train with the Gemma model.")
except Exception as e:
    print(f"\n❌ Login failed: {e}")
    sys.exit(1)
