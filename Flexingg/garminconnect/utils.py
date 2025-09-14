from django.utils import timezone
from .models import Garmin_Auth
import garth
import logging

logger = logging.getLogger(__name__)

def ensure_valid_tokens(garmin_auth):
    """
    Ensure Garmin tokens are valid by refreshing if expired.
    Returns True if successful, False otherwise.
    """
    if not garmin_auth.expired():
        return True

    logger.info(f"Tokens expired for user {garmin_auth.user.id}, refreshing...")
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

        # Create token objects
        oauth1_token = garth.auth_tokens.OAuth1Token(**oauth1_data)
        oauth2_token = garth.auth_tokens.OAuth2Token(**oauth2_data)

        # Refresh
        oauth1_token.refresh()
        oauth2_token.refresh()

        # Update stored tokens
        garmin_auth.oauth_token = oauth1_token.oauth_token
        garmin_auth.oauth_token_secret = oauth1_token.oauth_token_secret
        garmin_auth.mfa_token = getattr(oauth1_token, 'mfa_token', None)
        garmin_auth.mfa_expiration_timestamp = getattr(oauth1_token, 'mfa_expiration_timestamp', None)
        garmin_auth.domain = getattr(oauth1_token, 'domain', None)
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
        logger.info("Token refresh successful")
        return True
    except Exception as refresh_err:
        logger.error(f"Token refresh failed for user {garmin_auth.user.id}: {refresh_err}")
        return False