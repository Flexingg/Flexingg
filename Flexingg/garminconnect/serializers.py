from rest_framework import serializers
from .models import (
    Garmin_Auth, GarminCredentials, GarminDailySteps,
    GarminActivity, GarminBodyWeight
)

class Garmin_AuthSerializer(serializers.ModelSerializer):
    class Meta:
        model = Garmin_Auth
        fields = [
            'user', 'oauth_token', 'oauth_token_secret', 'mfa_token',
            'mfa_expiration_timestamp', 'domain', 'scope', 'jti', 'token_type',
            'access_token', 'refresh_token', 'expires_in', 'expires_at',
            'refresh_token_expires_in', 'refresh_token_expires_at',
            'last_sync', 'last_sync_attempt', 'garmin_email', 'liftosaur_user_id'
        ]

class GarminCredentialsSerializer(serializers.ModelSerializer):
    class Meta:
        model = GarminCredentials
        fields = [
            'id', 'user', 'garmin_email', 'session_data',
            'last_sync', 'created_at', 'updated_at'
        ]

class GarminDailyStepsSerializer(serializers.ModelSerializer):
    class Meta:
        model = GarminDailySteps
        fields = ['id', 'user', 'date', 'steps']

class GarminActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = GarminActivity
        fields = [
            'id', 'user', 'activity_id', 'name', 'activity_type',
            'start_time_utc', 'duration_seconds', 'distance_meters',
            'calories', 'average_hr', 'max_hr', 'raw_data', 'synced_at'
        ]

class GarminBodyWeightSerializer(serializers.ModelSerializer):
    class Meta:
        model = GarminBodyWeight
        fields = ['id', 'user', 'weight_kg', 'datetime', 'source_type', 'raw_data']