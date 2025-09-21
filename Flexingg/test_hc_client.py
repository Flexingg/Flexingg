#!/usr/bin/env python
"""
Test script to verify HCGatewayClient is using the correct API endpoint.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Flexingg.settings')
django.setup()

from healthconnect.utils import HCGatewayClient

def test_client_base_url():
    """Test that the client uses the correct base URL."""
    client = HCGatewayClient()
    expected_url = 'https://api.hcgateway.shuchir.dev/api/v2'
    actual_url = client.base_url

    print(f"Expected base URL: {expected_url}")
    print(f"Actual base URL: {actual_url}")

    if actual_url == expected_url:
        print("✅ SUCCESS: Client is using the correct API endpoint!")
        return True
    else:
        print("❌ FAILURE: Client is using the wrong API endpoint!")
        return False

if __name__ == '__main__':
    success = test_client_base_url()
    sys.exit(0 if success else 1)