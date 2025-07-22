"""
SSL/TLS Hostname Verification Fix

This module provides utilities to handle SSL hostname verification issues
that commonly occur when making HTTPS requests in Python.

The error "check_hostname requires server_hostname" typically occurs when:
1. Using urllib.request.urlopen() with HTTPS URLs
2. SSL context is not properly configured
3. Network/proxy configuration issues

Usage:
    from ssl_fix import create_ssl_context, safe_urlopen
    
    # For urllib.request
    ssl_context = create_ssl_context()
    response = urllib.request.urlopen(url, context=ssl_context)
    
    # Or use the convenience function
    response = safe_urlopen(url)
"""

import ssl
import urllib.request
import requests
from typing import Optional, Dict, Any


def create_ssl_context(verify_hostname: bool = False, verify_cert: bool = False) -> ssl.SSLContext:
    """
    Create an SSL context with configurable verification settings.
    
    Args:
        verify_hostname: Whether to verify the hostname in the certificate
        verify_cert: Whether to verify the SSL certificate
    
    Returns:
        Configured SSL context
    """
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = verify_hostname
    ssl_context.verify_mode = ssl.CERT_REQUIRED if verify_cert else ssl.CERT_NONE
    return ssl_context


def safe_urlopen(url: str, headers: Optional[Dict[str, str]] = None, 
                 verify_hostname: bool = False, verify_cert: bool = False) -> Any:
    """
    Safely open a URL with configurable SSL verification.
    
    Args:
        url: The URL to open
        headers: Optional headers to include in the request
        verify_hostname: Whether to verify the hostname
        verify_cert: Whether to verify the SSL certificate
    
    Returns:
        Response object from urllib.request.urlopen
    """
    ssl_context = create_ssl_context(verify_hostname, verify_cert)
    
    if headers:
        request = urllib.request.Request(url, headers=headers)
    else:
        request = urllib.request.Request(url)
    
    return urllib.request.urlopen(request, context=ssl_context)


def safe_requests_get(url: str, headers: Optional[Dict[str, str]] = None, 
                     verify: bool = False, **kwargs) -> requests.Response:
    """
    Safely make a GET request using requests library with configurable SSL verification.
    
    Args:
        url: The URL to request
        headers: Optional headers to include
        verify: Whether to verify SSL certificates
        **kwargs: Additional arguments to pass to requests.get
    
    Returns:
        Response object from requests.get
    """
    if headers is None:
        headers = {}
    
    return requests.get(url, headers=headers, verify=verify, **kwargs)


# Example usage functions
def download_file_safe(url: str, filepath: str, headers: Optional[Dict[str, str]] = None) -> None:
    """
    Safely download a file from a URL with SSL verification disabled.
    
    Args:
        url: The URL to download from
        filepath: Local path to save the file
        headers: Optional headers for the request
    """
    try:
        response = safe_urlopen(url, headers=headers)
        with open(filepath, 'wb') as f:
            f.write(response.read())
        print(f"Successfully downloaded {url} to {filepath}")
    except Exception as e:
        print(f"Error downloading {url}: {e}")


def api_request_safe(url: str, headers: Optional[Dict[str, str]] = None) -> Optional[Dict]:
    """
    Safely make an API request with SSL verification disabled.
    
    Args:
        url: The API URL
        headers: Optional headers for the request
    
    Returns:
        JSON response as dictionary, or None if failed
    """
    try:
        response = safe_requests_get(url, headers=headers, verify=False)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error making API request to {url}: {e}")
        return None


if __name__ == "__main__":
    # Example usage
    print("SSL Fix Module - Example Usage")
    
    # Test with a simple HTTPS request
    test_url = "https://httpbin.org/json"
    try:
        response = safe_requests_get(test_url, verify=False)
        print(f"Test request successful: {response.status_code}")
    except Exception as e:
        print(f"Test request failed: {e}") 