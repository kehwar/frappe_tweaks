import base64
import frappe
from frappe.core.doctype.user.user import User


def validate_user_password():
    """
    Custom authentication hook for validating user password as API credentials.
    
    This hook allows users to authenticate using their username and password
    in the Authorization header (instead of API key/secret).
    
    If validation succeeds, the user is authenticated. If it fails, the function
    returns without action, allowing Frappe's standard authentication flow to continue.
    """
    # Get the Authorization header from the request
    auth_header = frappe.get_request_header("Authorization")
    
    if not auth_header:
        # No Authorization header, let Frappe handle it
        return
    
    # Parse the authorization header to extract username and password
    username, password = parse_authorization_header(auth_header)
    
    if not username or not password:
        # Could not parse credentials, let Frappe handle it
        return
    
    # Try to validate username and password as user credentials
    validate_api_token_as_user_password(username, password)


def parse_authorization_header(auth_header):
    """
    Parse the Authorization header to extract username and password.
    
    Supports both "token" and "Basic" authentication schemes.
    
    Args:
        auth_header: The Authorization header value
        
    Returns:
        tuple: (username, password) or (None, None) if parsing fails
    """
    # Token authentication: "token username:password"
    if auth_header.startswith("token "):
        token = auth_header[6:]  # Remove 'token ' prefix
        try:
            username, password = token.split(":", 1)
            return username, password
        except ValueError:
            return None, None
    
    # Basic authentication: "Basic base64(username:password)"
    if auth_header.startswith("Basic "):
        try:
            encoded_credentials = auth_header[6:]  # Remove 'Basic ' prefix
            decoded_credentials = base64.b64decode(encoded_credentials).decode("utf-8")
            username, password = decoded_credentials.split(":", 1)
            return username, password
        except (ValueError, Exception):
            return None, None
    
    return None, None


def validate_api_token_as_user_password(username, password):
    """
    Validate username and password as user credentials.
    
    This allows users to authenticate with their username and password
    in the Authorization header instead of API key/secret pairs.
    
    Args:
        username: Username
        password: User password
    """
    credentials = User.find_by_credentials(user_name=username, password=password)

    if credentials and credentials.enabled and credentials.is_authenticated:
        # Store `form_dict`, because `set_user` clears it.
        form_dict = frappe.local.form_dict
        # Set the user as authenticated.
        frappe.set_user(username)
        # Restore `form_dict`.
        frappe.local.form_dict = form_dict