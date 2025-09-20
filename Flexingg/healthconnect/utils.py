import requests
from datetime import datetime, timedelta
from django.utils import timezone
import json
import os


class HCGatewayClient:
    METHODS = [
        'activeCaloriesBurned', 'basalBodyTemperature', 'basalMetabolicRate', 'bloodGlucose',
        'bloodPressure', 'bodyFat', 'bodyTemperature', 'boneMass', 'cervicalMucus', 'distance',
        'exerciseSession', 'elevationGained', 'floorsClimbed', 'heartRate', 'height', 'hydration',
        'leanBodyMass', 'menstruationFlow', 'menstruationPeriod', 'nutrition', 'ovulationTest',
        'oxygenSaturation', 'power', 'respiratoryRate', 'restingHeartRate', 'sleepSession',
        'speed', 'steps', 'stepsCadence', 'totalCaloriesBurned', 'vo2Max', 'weight', 'wheelchairPushes'
    ]


    def __init__(self):
        base_url = os.environ.get('HC_CONNECT_URL', 'http://localhost:6644')
        self.base_url = base_url + '/api/v2'
        self.session = requests.Session()
        self.token = None
        self.refresh_token = None
        self.expiry = None

    def _get_headers(self):
        if self.token:
            return {'Authorization': f'Bearer {self.token}'}
        return {}

    def login(self, username, password):
        """
        Login to HCGateway and get tokens.
        Returns: dict with token, refresh, expiry or raises Exception on failure.
        """
        url = f"{self.base_url}/login"
        data = {"username": username, "password": password}
        response = self.session.post(url, json=data)
        response.raise_for_status()
        result = response.json()
        self.token = result['token']
        self.refresh_token = result['refresh']
        self.expiry = timezone.datetime.fromisoformat(result['expiry'].replace('Z', '+00:00'))
        return result

    def refresh(self):
        """
        Refresh the access token using refresh_token.
        Returns: updated tokens or raises Exception.
        """
        if not self.refresh_token:
            raise ValueError("No refresh token available")
        url = f"{self.base_url}/refresh"
        data = {"refresh": self.refresh_token}
        response = self.session.post(url, json=data)
        response.raise_for_status()
        result = response.json()
        self.token = result['token']
        self.refresh_token = result['refresh']
        self.expiry = timezone.datetime.fromisoformat(result['expiry'].replace('Z', '+00:00'))
        return result

    def revoke(self):
        """
        Revoke all tokens.
        """
        if not self.token:
            return
        url = f"{self.base_url}/revoke"
        headers = self._get_headers()
        response = self.session.post(url, headers=headers)
        response.raise_for_status()
        self.token = None
        self.refresh_token = None
        self.expiry = None

    def is_authenticated(self):
        """
        Check if token is valid (set and not expired).
        """
        if not self.token or not self.expiry:
            return False

        # Ensure both datetimes are timezone-aware for proper comparison
        now = timezone.now()
        if self.expiry.tzinfo is None:
            expiry_aware = timezone.make_aware(self.expiry)
        else:
            expiry_aware = self.expiry

        return now < expiry_aware

    def _ensure_auth(self):
        """
        Ensure valid token, refresh if needed.
        """
        if not self.is_authenticated():
            if self.refresh_token:
                self.refresh()
            else:
                raise ValueError("No valid authentication. Login required.")

    def fetch(self, method, query=None):
        """
        Fetch data for a specific method.
        query: dict for MongoDB filter, e.g., {"start": {"$gte": "2023-01-01T00:00:00Z"}}
        Returns: list of data objects.
        """
        if method not in self.METHODS:
            raise ValueError(f"Invalid method: {method}")
        self._ensure_auth()
        url = f"{self.base_url}/fetch/{method}"
        headers = self._get_headers()
        data = {"queries": query} if query else {}
        response = self.session.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()

    def fetch_all_methods(self, start_date=None):
        """
        Fetch data for all methods.
        If start_date (datetime), filter from that date onward.
        Returns: dict {method: list of records}
        """
        results = {}
        query = None
        if start_date:
            # Ensure start_date is timezone-aware and convert to UTC for proper comparison
            if start_date.tzinfo is None:
                start_date = timezone.make_aware(start_date)
            # Convert to UTC and format as ISO string with Z suffix
            from datetime import timezone as dt_timezone
            utc_start = start_date.astimezone(dt_timezone.utc)
            iso_start = utc_start.isoformat().replace('+00:00', 'Z')
            query = {"start": {"$gte": iso_start}}
        for method in self.METHODS:
            try:
                results[method] = self.fetch(method, query)
            except Exception as e:
                print(f"Error fetching {method}: {e}")
                results[method] = []
        return results

    def fetch_historical(self, days=90):
        """
        Fetch historical data from last N days.
        """
        start_date = timezone.now() - timedelta(days=days)
        return self.fetch_all_methods(start_date)

    def fetch_recent(self, hours=24):
        """
        Fetch recent data from last N hours.
        """
        start_date = timezone.now() - timedelta(hours=hours)
        return self.fetch_all_methods(start_date)

    def delete(self, method, uuids):
        """
        Request deletion for records of a specific method.
        uuids: string or list of uuids to delete.
        Returns: dict with success and message.
        """
        if method not in self.METHODS:
            raise ValueError(f"Invalid method: {method}")
        self._ensure_auth()
        if isinstance(uuids, str):
            uuids = [uuids]
        url = f"{self.base_url}/delete/{method}"
        headers = self._get_headers()
        data = {"uuid": uuids}
        response = self.session.delete(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()
from .models import HealthConnectData
from django.utils import timezone
from decimal import Decimal


def get_daily_consumed_calories(profile, date_obj=None):
    """
    Compute total consumed calories (kcal) for a given day from nutrition records.
    
    Args:
        profile: UserProfile instance
        date_obj: date object for the day; defaults to today in local time
    
    Returns:
        int: Total kcal, rounded to nearest integer, or 0 if no data
    """
    if date_obj is None:
        today = timezone.localtime().date()
    else:
        today = date_obj
    
    records = HealthConnectData.objects.filter(
        profile=profile,
        method='nutrition',
        start_time__date=today
    )
    
    total = Decimal('0')
    for record in records:
        data = record.data
        if isinstance(data, dict) and 'energy' in data:
            energy = data['energy']
            if isinstance(energy, dict) and 'inKilocalories' in energy:
                try:
                    kcal = Decimal(str(energy['inKilocalories']))
                    total += kcal
                except (ValueError, TypeError, InvalidOperation):
                    pass  # Skip invalid values
    
    return int(total.quantize(Decimal('1')))