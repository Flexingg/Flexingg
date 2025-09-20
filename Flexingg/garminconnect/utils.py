from django.utils import timezone
from .models import Garmin_Auth
import garth
import logging

logger = logging.getLogger(__name__)

def configure_garmin_client(auth_data):
    """
    Configure the Garth client with existing tokens from ConnectedService auth_data or Garmin_Auth model.
    Does not refresh tokens; assumes they are valid.
    Returns True if configured successfully.
    """
    try:
        # Handle both nested structure (from ConnectedService) and flat structure (from Garmin_Auth)
        if isinstance(auth_data, dict):
            # Check if it's already nested (ConnectedService format)
            oauth1_data = auth_data.get('oauth1', {})
            oauth2_data = auth_data.get('oauth2', {})

            # If not nested, assume it's flat structure (Garmin_Auth format)
            if not oauth1_data and not oauth2_data:
                # Flat structure - extract OAuth1 and OAuth2 data
                oauth1_fields = ['oauth_token', 'oauth_token_secret', 'mfa_token', 'mfa_expiration_timestamp', 'domain']
                oauth2_fields = ['scope', 'jti', 'token_type', 'access_token', 'refresh_token', 'expires_in', 'expires_at', 'refresh_token_expires_in', 'refresh_token_expires_at']

                oauth1_data = {field: auth_data.get(field) for field in oauth1_fields if auth_data.get(field) is not None}
                oauth2_data = {field: auth_data.get(field) for field in oauth2_fields if auth_data.get(field) is not None}
        else:
            # Handle Garmin_Auth model instance
            oauth1_data = {
                'oauth_token': getattr(auth_data, 'oauth_token', None),
                'oauth_token_secret': getattr(auth_data, 'oauth_token_secret', None),
                'mfa_token': getattr(auth_data, 'mfa_token', None),
                'mfa_expiration_timestamp': getattr(auth_data, 'mfa_expiration_timestamp', None),
                'domain': getattr(auth_data, 'domain', None),
            }
            oauth2_data = {
                'scope': getattr(auth_data, 'scope', None),
                'jti': getattr(auth_data, 'jti', None),
                'token_type': getattr(auth_data, 'token_type', None),
                'access_token': getattr(auth_data, 'access_token', None),
                'refresh_token': getattr(auth_data, 'refresh_token', None),
                'expires_in': getattr(auth_data, 'expires_in', None),
                'expires_at': getattr(auth_data, 'expires_at', None),
                'refresh_token_expires_in': getattr(auth_data, 'refresh_token_expires_in', None),
                'refresh_token_expires_at': getattr(auth_data, 'refresh_token_expires_at', None),
            }

        # Filter out None values
        oauth1_data = {k: v for k, v in oauth1_data.items() if v is not None}
        oauth2_data = {k: v for k, v in oauth2_data.items() if v is not None}

        # Check if oauth1_data has the minimum required fields
        oauth1_required = ['oauth_token', 'oauth_token_secret']
        if not oauth1_data or not all(field in oauth1_data for field in oauth1_required):
            logger.warning("OAuth1 data incomplete or missing required fields")
            return False

        # Check if oauth2_data has the minimum required fields
        oauth2_required = ['access_token', 'refresh_token', 'expires_at']
        if not oauth2_data or not all(field in oauth2_data for field in oauth2_required):
            logger.warning("OAuth2 data incomplete or missing required fields")
            return False

        oauth1_token = garth.auth_tokens.OAuth1Token(**oauth1_data)
        oauth2_token = garth.auth_tokens.OAuth2Token(**oauth2_data)
        garth.client.configure(oauth1_token=oauth1_token, oauth2_token=oauth2_token)
        logger.info("Garmin client configured with existing tokens.")
        return True
    except Exception as config_err:
        logger.error(f"Failed to configure Garmin client: {config_err}")
        return False

def refresh_oauth2_only(auth_data):
    """
    Refresh only the OAuth2 token if expired.
    Returns updated auth_data dict if successful, None otherwise.
    """
    try:
        # Handle both nested structure (from ConnectedService) and flat structure (from Garmin_Auth)
        if isinstance(auth_data, dict):
            # Check if it's already nested (ConnectedService format)
            oauth2_data = auth_data.get('oauth2', {})

            # If not nested, assume it's flat structure (Garmin_Auth format)
            if not oauth2_data:
                oauth2_fields = ['scope', 'jti', 'token_type', 'access_token', 'refresh_token', 'expires_in', 'expires_at', 'refresh_token_expires_in', 'refresh_token_expires_at']
                oauth2_data = {field: auth_data.get(field) for field in oauth2_fields if auth_data.get(field) is not None}
        else:
            # Handle Garmin_Auth model instance
            oauth2_data = {
                'scope': getattr(auth_data, 'scope', None),
                'jti': getattr(auth_data, 'jti', None),
                'token_type': getattr(auth_data, 'token_type', None),
                'access_token': getattr(auth_data, 'access_token', None),
                'refresh_token': getattr(auth_data, 'refresh_token', None),
                'expires_in': getattr(auth_data, 'expires_in', None),
                'expires_at': getattr(auth_data, 'expires_at', None),
                'refresh_token_expires_in': getattr(auth_data, 'refresh_token_expires_in', None),
                'refresh_token_expires_at': getattr(auth_data, 'refresh_token_expires_at', None),
            }

        # Filter out None values
        oauth2_data = {k: v for k, v in oauth2_data.items() if v is not None}

        # Check if oauth2_data has the minimum required fields
        required_fields = ['access_token', 'refresh_token', 'expires_at']
        if not oauth2_data or not all(field in oauth2_data for field in required_fields):
            logger.warning("OAuth2 data incomplete or missing required fields")
            return None

        # Check if token is expired
        expires_at = oauth2_data.get('expires_at')
        if expires_at and expires_at >= timezone.now().timestamp():
            logger.info("Tokens still valid, no refresh needed.")
            return auth_data

        logger.info("Tokens expired, refreshing OAuth2...")
        oauth2_token = garth.auth_tokens.OAuth2Token(**oauth2_data)
        oauth2_token.refresh()

        # Update stored OAuth2 tokens in auth_data
        if isinstance(auth_data, dict):
            # For dict structure, update the nested oauth2 section
            if 'oauth2' not in auth_data:
                auth_data['oauth2'] = {}
            auth_data['oauth2'].update({
                'scope': oauth2_token.scope,
                'jti': oauth2_token.jti,
                'token_type': oauth2_token.token_type,
                'access_token': oauth2_token.access_token,
                'refresh_token': oauth2_token.refresh_token,
                'expires_in': oauth2_token.expires_in,
                'expires_at': oauth2_token.expires_at,
                'refresh_token_expires_in': getattr(oauth2_token, 'refresh_token_expires_in', None),
                'refresh_token_expires_at': getattr(oauth2_token, 'refresh_token_expires_at', None),
            })
        else:
            # For model instance, update the individual fields
            auth_data.scope = oauth2_token.scope
            auth_data.jti = oauth2_token.jti
            auth_data.token_type = oauth2_token.token_type
            auth_data.access_token = oauth2_token.access_token
            auth_data.refresh_token = oauth2_token.refresh_token
            auth_data.expires_in = oauth2_token.expires_in
            auth_data.expires_at = oauth2_token.expires_at
            auth_data.refresh_token_expires_in = getattr(oauth2_token, 'refresh_token_expires_in', None)
            auth_data.refresh_token_expires_at = getattr(oauth2_token, 'refresh_token_expires_at', None)
            auth_data.save()

        logger.info("OAuth2 token refresh successful")
        return auth_data
    except Exception as refresh_err:
        logger.error(f"OAuth2 token refresh failed: {refresh_err}")
        return None