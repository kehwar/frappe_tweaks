import frappe
from frappe.core.doctype.user.user import User


def validate_api_key_secret(api_key, api_secret, frappe_authorization_source=None):
    """
    Custom authentication hook for validating API key and secret.
    
    This hook extends Frappe's default authentication to support username/password
    as API key/secret in addition to the standard API key validation.
    
    Args:
        api_key: The API key or username
        api_secret: The API secret or password
        frappe_authorization_source: Source of the authorization header
    """
    # Try to validate API key and secret as user credentials first.
    if validate_api_token_as_user_password(api_key, api_secret):
        return
    
    # If that fails, fall back to the original `validate_api_key_secret` function.
    from frappe.auth import validate_api_key_secret as frappe_validate_api_key_secret
    return frappe_validate_api_key_secret(api_key, api_secret, frappe_authorization_source)


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