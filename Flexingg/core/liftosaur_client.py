import logging
import requests

logger = logging.getLogger(__name__)


def liftosaur_download(liftosaur_id, session_token):
    """
    Fetches the latest workout data from the Liftosaur API for a given user ID.
    """
    url = f'https://api3.liftosaur.com/api/storage?tempuserid={liftosaur_id}'
    headers = {'Cookie': f'session={session_token}'}

    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching data from Liftosaur API: {e}")
        return None