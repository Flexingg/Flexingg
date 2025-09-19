from django.test import TestCase
from django.utils import timezone
from datetime import datetime, date
from .tasks import (
    normalize_garmin_activity_to_workout,
    normalize_liftosaur_workout,
    normalize_hc_sleep,
    normalize_garmin_steps,
    normalize_hc_steps
)

class NormalizationTests(TestCase):

    def test_normalize_garmin_activity_to_workout(self):
        activity = {
            'activityId': 12345,
            'startTimeGMT': 1672531200000,  # 2023-01-01 00:00:00 UTC
            'duration': 3600.0,
        }
        normalized = normalize_garmin_activity_to_workout(activity)
        self.assertEqual(normalized['source_id'], 12345)
        self.assertEqual(normalized['start_time'], timezone.make_aware(datetime(2023, 1, 1, 0, 0, 0)))
        self.assertEqual(normalized['end_time'], timezone.make_aware(datetime(2023, 1, 1, 1, 0, 0)))
        self.assertEqual(normalized['data'], activity)

    def test_normalize_liftosaur_workout(self):
        workout_data = {
            'id': 'abcd-1234',
            'timestamp': 1672531200000,
        }
        normalized = normalize_liftosaur_workout(workout_data)
        self.assertEqual(normalized['source_id'], 'abcd-1234')
        self.assertEqual(normalized['start_time'], timezone.make_aware(datetime(2023, 1, 1, 0, 0, 0)))
        self.assertEqual(normalized['end_time'], timezone.make_aware(datetime(2023, 1, 1, 1, 0, 0)))
        self.assertEqual(normalized['data'], workout_data)

    def test_normalize_hc_sleep(self):
        sleep_session = {
            '_id': 'sleep-123',
            'start': '2023-01-01T22:00:00',
            'end': '2023-01-02T06:00:00',
        }
        normalized = normalize_hc_sleep(sleep_session)
        self.assertEqual(normalized['source_id'], 'sleep-123')
        self.assertEqual(normalized['start_time'], timezone.make_aware(datetime(2023, 1, 1, 22, 0, 0)))
        self.assertEqual(normalized['end_time'], timezone.make_aware(datetime(2023, 1, 2, 6, 0, 0)))
        self.assertEqual(normalized['data'], sleep_session)

    def test_normalize_garmin_steps(self):
        day = {
            'calendarDate': '2023-01-01',
            'totalSteps': 10000,
        }
        normalized = normalize_garmin_steps(day)
        self.assertEqual(normalized['date'], date(2023, 1, 1))
        self.assertEqual(normalized['steps'], 10000)
        self.assertEqual(normalized['data'], day)

    def test_normalize_hc_steps(self):
        steps_record = {
            'start': '2023-01-01T00:00:00',
            'data': {
                'count': 5000
            }
        }
        normalized = normalize_hc_steps(steps_record)
        self.assertEqual(normalized['date'], date(2023, 1, 1))
        self.assertEqual(normalized['steps'], 5000)
        self.assertEqual(normalized['data'], steps_record)
