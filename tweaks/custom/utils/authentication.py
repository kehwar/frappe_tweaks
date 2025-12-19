import frappe
from frappe import auth
from frappe.core.doctype.user.user import User

def decorate_validate_api_key_secret(validate_api_key_secret):
    """Decorator for `auth.validate_api_key_secret`"""

    def _validate_api_key_secret(api_key, api_secret, frappe_authorization_source=None):

        # Try to validate API key and secret as user credentials first.
        if validate_api_token_as_user_password(api_key, api_secret):
            return
        
        # If that fails, fall back to the original `validate_api_key_secret` function.
        return validate_api_key_secret(api_key, api_secret, frappe_authorization_source)

    return _validate_api_key_secret

def validate_api_token_as_user_password(user, password):
    """Validate API token as user credentials."""

    credentials = User.find_by_credentials(user_name=user, password=password)

    if credentials and credentials.enabled and credentials.is_authenticated:
        # Store `form_dict`, because `set_user` clears it.
        form_dict = frappe.local.form_dict
        # Set the user as authenticated.
        frappe.set_user(user)
        # Restore `form_dict`.
        frappe.local.form_dict = form_dict
        return True

def apply_authentication_patches():
    """Apply authentication patches."""
    # refactor: Migrate to frappe/auth.py
    # - Update validate_api_key_secret to support username/password fallback
    # - Add validate_api_token_as_user_password logic before API key validation
    auth.validate_api_key_secret = decorate_validate_api_key_secret(auth.validate_api_key_secret)