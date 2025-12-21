import base64
import frappe
from frappe.core.doctype.user.user import User


def validate_user_password():
    """
    Custom authentication hook for validating user password as API credentials.
    
    This hook extends Frappe's default authentication to support username/password
    as API key/secret in addition to the standard API key validation.
    
    The function extracts credentials from the Authorization header and attempts
    to validate them as username/password before falling back to standard API key validation.
    """
    # Get the Authorization header from the request
    auth_header = frappe.get_request_header("Authorization")
    
    if not auth_header:
        # No Authorization header, let Frappe handle it
        return
    
    # Parse the authorization header to extract api_key and api_secret
    api_key, api_secret, auth_type = parse_authorization_header(auth_header)
    
    if not api_key or not api_secret:
        # Could not parse credentials, let Frappe handle it
        return
    
    # Try to validate API key and secret as user credentials first.
    if validate_api_token_as_user_password(api_key, api_secret):
        return
    
    # If that fails, fall back to the original `validate_api_key_secret` function.
    from frappe.auth import validate_api_key_secret as frappe_validate_api_key_secret
    return frappe_validate_api_key_secret(api_key, api_secret, auth_type)


def parse_authorization_header(auth_header):
    """
    Parse the Authorization header to extract api_key and api_secret.
    
    Supports both "token" and "Basic" authentication schemes.
    
    Args:
        auth_header: The Authorization header value
        
    Returns:
        tuple: (api_key, api_secret, auth_type) or (None, None, None) if parsing fails
    """
    # Token authentication: "token api_key:api_secret"
    if auth_header.startswith("token "):
        token = auth_header[6:]  # Remove 'token ' prefix
        try:
            api_key, api_secret = token.split(":", 1)
            return api_key, api_secret, "token"
        except ValueError:
            return None, None, None
    
    # Basic authentication: "Basic base64(api_key:api_secret)"
    if auth_header.startswith("Basic "):
        try:
            encoded_credentials = auth_header[6:]  # Remove 'Basic ' prefix
            decoded_credentials = base64.b64decode(encoded_credentials).decode("utf-8")
            api_key, api_secret = decoded_credentials.split(":", 1)
            return api_key, api_secret, "Basic"
        except (ValueError, Exception):
            return None, None, None
    
    return None, None, None


def validate_api_token_as_user_password(user, password):
    """
    Validate API token as user credentials.
    
    This allows users to authenticate with their username and password
    instead of API key/secret pairs.
    
    Args:
        user: Username
        password: User password
        
    Returns:
        bool: True if credentials are valid and user is authenticated, False otherwise
    """
    credentials = User.find_by_credentials(user_name=user, password=password)

    if credentials and credentials.enabled and credentials.is_authenticated:
        # Store `form_dict`, because `set_user` clears it.
        form_dict = frappe.local.form_dict
        # Set the user as authenticated.
        frappe.set_user(user)
        # Restore `form_dict`.
        frappe.local.form_dict = form_dict
        return True
    
    return False