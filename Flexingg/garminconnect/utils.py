from django.utils import timezone
from .models import Garmin_Auth
import garth
import logging

logger = logging.getLogger(__name__)

def configure_garmin_client(garmin_auth):
    """
    Configure the Garth client with existing tokens from Garmin_Auth.
    Does not refresh tokens; assumes they are valid.
    Returns True if configured successfully.
    """
    try:
        oauth1_data = {
            'oauth_token': garmin_auth.oauth_token,
            'oauth_token_secret': garmin_auth.oauth_token_secret,
            'mfa_token': getattr(garmin_auth, 'mfa_token', None),
            'mfa_expiration_timestamp': getattr(garmin_auth, 'mfa_expiration_timestamp', None),
            'domain': getattr(garmin_auth, 'domain', None),
        }
        oauth2_data = {
            'scope': garmin_auth.scope,
            'jti': garmin_auth.jti,
            'token_type': garmin_auth.token_type,
            'access_token': garmin_auth.access_token,
            'refresh_token': garmin_auth.refresh_token,
            'expires_in': garmin_auth.expires_in,
            'expires_at': garmin_auth.expires_at,
            'refresh_token_expires_in': getattr(garmin_auth, 'refresh_token_expires_in', None),
            'refresh_token_expires_at': getattr(garmin_auth, 'refresh_token_expires_at', None),
        }

        oauth1_token = garth.auth_tokens.OAuth1Token(**oauth1_data)
        oauth2_token = garth.auth_tokens.OAuth2Token(**oauth2_data)
        garth.client.configure(oauth1_token=oauth1_token, oauth2_token=oauth2_token)
        logger.info(f"Garmin client configured for user {garmin_auth.user.id} with existing tokens.")
        return True
    except Exception as config_err:
        logger.error(f"Failed to configure Garmin client for user {garmin_auth.user.id}: {config_err}")
        return False

def refresh_oauth2_only(garmin_auth):
    """
    Refresh only the OAuth2 token if expired.
    Returns True if successful, False otherwise.
    """
    if not garmin_auth.expired():
        logger.info(f"Tokens still valid for user {garmin_auth.user.id}, no refresh needed.")
        return True

    logger.info(f"Tokens expired for user {garmin_auth.user.id}, refreshing OAuth2...")
    try:
        oauth2_data = {
            'scope': garmin_auth.scope,
            'jti': garmin_auth.jti,
            'token_type': garmin_auth.token_type,
            'access_token': garmin_auth.access_token,
            'refresh_token': garmin_auth.refresh_token,
            'expires_in': garmin_auth.expires_in,
            'expires_at': garmin_auth.expires_at,
            'refresh_token_expires_in': getattr(garmin_auth, 'refresh_token_expires_in', None),
            'refresh_token_expires_at': getattr(garmin_auth, 'refresh_token_expires_at', None),
        }

        oauth2_token = garth.auth_tokens.OAuth2Token(**oauth2_data)
        oauth2_token.refresh()

        # Update stored OAuth2 tokens
        garmin_auth.scope = oauth2_token.scope
        garmin_auth.jti = oauth2_token.jti
        garmin_auth.token_type = oauth2_token.token_type
        garmin_auth.access_token = oauth2_token.access_token
        garmin_auth.refresh_token = oauth2_token.refresh_token
        garmin_auth.expires_in = oauth2_token.expires_in
        garmin_auth.expires_at = oauth2_token.expires_at
        garmin_auth.refresh_token_expires_in = getattr(oauth2_token, 'refresh_token_expires_in', None)
        garmin_auth.refresh_token_expires_at = getattr(oauth2_token, 'refresh_token_expires_at', None)
        garmin_auth.save()
        logger.info("OAuth2 token refresh successful for user {garmin_auth.user.id}")
        return True
    except Exception as refresh_err:
        logger.error(f"OAuth2 token refresh failed for user {garmin_auth.user.id}: {refresh_err}")
        return False