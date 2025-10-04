import logging
from decimal import Decimal, InvalidOperation
from django.db import transaction
from django.db.models import F
from typing import Any, Dict, Optional

from .models import (
    HealthConnectRawData,
    DailyHealthSummary,
    BodyWeight,
    SleepSession,
    NutritionEntry,
    StepRecord,
    ExerciseSession,
    BloodPressure,
    MetricSample,
    HydrationEntry,
    BodyComposition,
    MenstruationPeriod,
)
from django.utils import timezone
from core.models import Sleep as CoreSleep

logger = logging.getLogger(__name__)


def _to_decimal(value: Any, default: Decimal = Decimal('0')) -> Decimal:
    try:
        if value is None or value == '':
            return default
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return default


def _get_or_create_summary(profile, date):
    summary, _ = DailyHealthSummary.objects.get_or_create(profile=profile, date=date)
    return summary


def normalize_and_aggregate_record(record: HealthConnectRawData):
    """
    Entry point to normalize a staged HealthConnectRawData record into the
    appropriate normalized model and update DailyHealthSummary for aggregatable types.
    """
    handler_map = {
        'steps': _handle_steps,
        'step': _handle_steps,
        'stepsCadence': _handle_steps_cadence,
        'nutrition': _handle_nutrition,
        'weight': _handle_weight,
        'hydration': _handle_hydration,
        'sleepSession': _handle_sleep,
        'sleep': _handle_sleep,
        'exerciseSession': _handle_exercise,
        'activeCaloriesBurned': _handle_active_calories,
        'totalCaloriesBurned': _handle_active_calories,
        'heartRate': _handle_metric,
        'restingHeartRate': _handle_metric,
        'oxygenSaturation': _handle_metric,
        'respiratoryRate': _handle_metric,
        'vo2Max': _handle_metric,
        'bloodPressure': _handle_blood_pressure,
        'bodyFat': _handle_body_composition,
        'bodyComposition': _handle_body_composition,
        'menstruationFlow': _handle_menstruation,
        'menstruationPeriod': _handle_menstruation,
        # add more mappings as needed
    }

    method = (record.method or '').strip()
    handler = handler_map.get(method, _handle_fallback_metric)
    try:
        handler(record)
    except Exception as e:
        logger.exception("Failed to normalize record %s (%s): %s", record.record_id, method, e)


def _handle_steps(record: HealthConnectRawData):
    """
    Normalizes steps records into StepRecord and increments DailyHealthSummary.steps_total.
    Accepts a few common shapes from Health Connect payloads.
    """
    data = record.data or {}
    # common field names: 'steps', 'count', 'value', 'total'
    steps_val = None
    for key in ('steps', 'count', 'value', 'totalSteps', 'total'):
        if key in data:
            steps_val = data.get(key)
            break

    try:
        steps_int = int(steps_val) if steps_val is not None else 0
    except (TypeError, ValueError):
        steps_int = 0

    # save discrete step record when there is a source id
    StepRecord.objects.update_or_create(
        source_id=record.record_id,
        defaults={
            'user': record.profile,
            'source': 'healthconnect',
            'start_time': record.start_time,
            'end_time': record.end_time,
            'steps': steps_int,
            'cadence': _to_decimal(data.get('cadence')) if data.get('cadence') else None,
            'distance_meters': _to_decimal(data.get('distance', {}).get('inMeters') if isinstance(data.get('distance'), dict) else data.get('distance')) if data.get('distance') else None,
            'data': data,
        }
    )

    if steps_int:
        summary = _get_or_create_summary(record.profile, record.start_time.date())
        # atomic increment
        DailyHealthSummary.objects.filter(pk=summary.pk).update(steps_total=F('steps_total') + steps_int)


def _handle_steps_cadence(record: HealthConnectRawData):
    # Map cadence/time-series steps where appropriate to MetricSample or StepRecord depending on payload
    data = record.data or {}
    # If there is a steps count include it
    if data.get('steps') or data.get('count'):
        _handle_steps(record)
        return

    # otherwise create a metric sample for cadence
    value = data.get('cadence') or data.get('value')
    MetricSample.objects.create(
        user=record.profile,
        source='healthconnect',
        source_id=record.record_id,
        datetime=record.start_time,
        metric='stepsCadence',
        value=_to_decimal(value),
        unit=data.get('unit') or 'steps/min' if value else None,
        data=data,
    )


def _handle_nutrition(record: HealthConnectRawData):
    """
    Extracts calories/protein/carbs/fat from nutrition payloads and updates DailyHealthSummary.
    Handles a few possible structures and normalizes calories to kilocalories (kcal).
    """
    data = record.data or {}

    # Helper to extract nutrient grams from a variety of shapes
    def _get_nutrient(*keys):
        for key in keys:
            val = data.get(key)
            if val is None:
                continue
            if isinstance(val, dict):
                # e.g. {'inGrams': 25}
                g = val.get('inGrams') or val.get('in_grams') or val.get('grams')
                if g is not None:
                    return g
            else:
                return val
        return None

    # Prefer explicit kilocalorie fields, otherwise convert common alternatives
    calories = None
    energy = data.get('energy') or {}
    if isinstance(energy, dict):
        # Look for kilocalorie fields first
        calories = energy.get('inKilocalories') or energy.get('inKcal') or energy.get('inKilocalorie')
        # If only inCalories present and it's numeric, assume it's calories (not kcal) and convert -> kcal
        if calories is None and ('inCalories' in energy or 'inCalories' in energy.keys()):
            raw = energy.get('inCalories')
            try:
                # Convert calories (e.g., 500000) -> kcal by dividing by 1000 if it looks like calories
                calories = Decimal(str(raw)) / Decimal('1000')
            except Exception:
                # fallback to raw value
                calories = raw
    # Fallback to top-level fields if energy dict wasn't usable
    if calories is None:
        calories = data.get('calories') or data.get('kcal') or data.get('calorie') or data.get('energy')

    # Extract protein / carbs / fat from common fields and vendor-specific names
    protein = _get_nutrient('protein', 'protein_grams', 'proteinInGrams')
    carbs = _get_nutrient('carbs', 'carbs_grams', 'carbohydrates', 'totalCarbohydrate', 'totalCarbohydrates', 'total_carbohydrate')
    fat = _get_nutrient('fat', 'fat_grams', 'totalFat', 'total_Fat', 'total_fat')

    # Convert to Decimal safely
    calories_dec = _to_decimal(calories, Decimal('0'))
    # If calories_dec looks like joules (very large), convert to kcal conservatively (/4.184)
    if calories_dec > Decimal('100000'):
        try:
            calories_dec = (calories_dec / Decimal('4.184')).quantize(Decimal('0.01'))
        except Exception:
            pass

    protein_dec = _to_decimal(protein, Decimal('0'))
    carbs_dec = _to_decimal(carbs, Decimal('0'))
    fat_dec = _to_decimal(fat, Decimal('0'))

    # Persist NutritionEntry (one normalized row per source record)
    NutritionEntry.objects.update_or_create(
        source_id=record.record_id,
        defaults={
            'user': record.profile,
            'source': 'healthconnect',
            'datetime': record.start_time,
            'calories': calories_dec if calories_dec != Decimal('0') else None,
            'protein_grams': protein_dec if protein_dec != Decimal('0') else None,
            'carbs_grams': carbs_dec if carbs_dec != Decimal('0') else None,
            'fat_grams': fat_dec if fat_dec != Decimal('0') else None,
            'data': data,
        }
    )

    # Update Daily summary atomically (kcal / grams)
    summary = _get_or_create_summary(record.profile, record.start_time.date())
    with transaction.atomic():
        updates = {}
        if calories_dec and calories_dec != Decimal('0'):
            updates['calories_total'] = F('calories_total') + calories_dec
        if protein_dec and protein_dec != Decimal('0'):
            updates['protein_grams_total'] = F('protein_grams_total') + protein_dec
        if carbs_dec and carbs_dec != Decimal('0'):
            updates['carbs_grams_total'] = F('carbs_grams_total') + carbs_dec
        if fat_dec and fat_dec != Decimal('0'):
            updates['fat_grams_total'] = F('fat_grams_total') + fat_dec

        if updates:
            DailyHealthSummary.objects.filter(pk=summary.pk).update(**updates)


def _handle_weight(record: HealthConnectRawData):
    """
    Normalize weight entries. Handles multiple unit keys and prefers direct pound values when available.
    """
    data = record.data or {}
    weight_lbs = None

    w = data.get('weight')
    # If weight is a dict with multiple unit keys, try several fallbacks
    if isinstance(w, dict):
        # Prefer explicit pound fields when present
        weight_lbs = w.get('inPounds') or w.get('inPound') or w.get('inPoundsValue') or w.get('inPoundsValue')
        # Try common keys
        if weight_lbs is None:
            # kilograms -> convert
            kg = w.get('inKilograms') or w.get('inKg') or w.get('kg')
            if kg is not None:
                try:
                    weight_lbs = _to_decimal(kg) * Decimal('2.20462')
                except Exception:
                    weight_lbs = None
        if weight_lbs is None:
            # grams / milligrams -> convert
            grams = w.get('inGrams') or w.get('grams')
            if grams is not None:
                try:
                    weight_lbs = _to_decimal(grams) / Decimal('453.59237')
                except Exception:
                    weight_lbs = None
        if weight_lbs is None:
            # ounces
            ounces = w.get('inOunces') or w.get('inOunce') or w.get('ounces')
            if ounces is not None:
                try:
                    weight_lbs = _to_decimal(ounces) / Decimal('16')
                except Exception:
                    weight_lbs = None
    else:
        # Non-dict shapes: maybe a raw number in kg or lbs; try a few fallbacks
        if data.get('unit') and 'kg' in str(data.get('unit')).lower():
            weight_lbs = (_to_decimal(data.get('value')) * Decimal('2.20462')) if data.get('value') else None
        else:
            # try top-level keys
            weight_lbs = data.get('inPounds') or data.get('inPoundsValue') or data.get('inPounds') or data.get('pounds') or data.get('inPoundsValue')
            if weight_lbs is None:
                kg_val = data.get('inKilograms') or data.get('inKg') or data.get('kg') or data.get('value')
                if kg_val is not None:
                    try:
                        weight_lbs = _to_decimal(kg_val) * Decimal('2.20462')
                    except Exception:
                        weight_lbs = None

    if weight_lbs is None:
        return

    try:
        weight_lbs_dec = _to_decimal(weight_lbs).quantize(Decimal('0.01'))
    except Exception:
        logger.exception("Invalid weight value for record %s: %s", record.record_id, weight_lbs)
        return

    BodyWeight.objects.update_or_create(
        source_id=record.record_id,
        defaults={
            'user': record.profile,
            'source': 'healthconnect',
            'datetime': record.start_time,
            'weight_lbs': weight_lbs_dec,
            'data': data,
        }
    )


def _handle_hydration(record: HealthConnectRawData):
    """
    Normalize hydration entries and update daily water total (converting ml -> ounces).
    """
    data = record.data or {}
    vol_ml = None
    vol = data.get('volume') or data.get('amount') or data.get('hydrationVolume')
    if isinstance(vol, dict):
        vol_ml = vol.get('inMilliliters') or vol.get('ml') or vol.get('in_milliliters')
    else:
        vol_ml = vol or data.get('volume_ml') or data.get('ml')

    vol_ml_dec = _to_decimal(vol_ml, Decimal('0'))
    if vol_ml_dec == Decimal('0'):
        return

    # create or update hydration entry
    HydrationEntry.objects.update_or_create(
        source_id=record.record_id,
        defaults={
            'user': record.profile,
            'source': 'healthconnect',
            'datetime': record.start_time,
            'volume_ml': vol_ml_dec,
            'volume_ounces': (vol_ml_dec * Decimal('0.033814')).quantize(Decimal('0.01')),
            'data': data,
        }
    )

    # update daily summary ounces
    summary = _get_or_create_summary(record.profile, record.start_time.date())
    DailyHealthSummary.objects.filter(pk=summary.pk).update(
        water_ounces_total=F('water_ounces_total') + (vol_ml_dec * Decimal('0.033814'))
    )


def _handle_sleep(record: HealthConnectRawData):
    """
    Normalize sleep sessions.
    Writes both the HealthConnect SleepSession (detailed) and a unified core.Sleep
    record so the rest of the system can consume sleep data the same way as other sources.
    """
    data = record.data or {}

    # Determine start/end defensively (prefer the record timestamps but fall back to payload)
    start_time = record.start_time or None
    end_time = record.end_time or None
    # payload keys sometimes use startTime/endTime (camelCase)
    if not start_time:
        s = data.get('startTime') or data.get('start') or data.get('start_time')
        try:
            if isinstance(s, str):
                s_val = s.replace('Z', '+00:00')
                start_time = timezone.datetime.fromisoformat(s_val)
        except Exception:
            start_time = None
    if not end_time:
        e = data.get('endTime') or data.get('end') or data.get('end_time')
        try:
            if isinstance(e, str):
                e_val = e.replace('Z', '+00:00')
                end_time = timezone.datetime.fromisoformat(e_val)
        except Exception:
            end_time = None

    # Persist the detailed HealthConnect sleep session
    SleepSession.objects.update_or_create(
        source_id=record.record_id,
        defaults={
            'user': record.profile,
            'source': 'healthconnect',
            'start_time': start_time or record.start_time,
            'end_time': end_time or record.end_time,
            'data': data,
        }
    )

    # Normalize stages if present: convert ISO strings to datetimes for the core sleep data payload
    stages = data.get('stages') or []
    normalized_stages = []
    for s in stages:
        try:
            s_start = s.get('startTime') or s.get('start') or s.get('startTimeUTC')
            s_end = s.get('endTime') or s.get('end') or s.get('endTimeUTC')
            ns = {}
            if isinstance(s_start, str):
                try:
                    ns['start_time'] = timezone.datetime.fromisoformat(s_start.replace('Z', '+00:00'))
                except Exception:
                    ns['start_time'] = s_start
            else:
                ns['start_time'] = s_start
            if isinstance(s_end, str):
                try:
                    ns['end_time'] = timezone.datetime.fromisoformat(s_end.replace('Z', '+00:00'))
                except Exception:
                    ns['end_time'] = s_end
            else:
                ns['end_time'] = s_end
            ns['stage'] = s.get('stage')
            normalized_stages.append(ns)
        except Exception:
            continue

    # Compute duration seconds where possible
    duration_seconds = None
    try:
        if start_time and end_time:
            duration_seconds = (end_time - start_time).total_seconds()
    except Exception:
        duration_seconds = None

    # Persist a unified Sleep record for consumption by other parts of the app
    try:
        CoreSleep.objects.update_or_create(
            source_id=record.record_id,
            defaults={
                'user': record.profile,
                'source': 'healthconnect',
                'start_time': start_time or record.start_time,
                'end_time': end_time or record.end_time,
                'data': {
                    'original': data,
                    'stages': normalized_stages,
                    'duration_seconds': duration_seconds
                }
            }
        )
    except Exception:
        logger.exception("Failed to create unified Sleep for record %s", record.record_id)

    # Also update daily summary with total sleep minutes for the date of the start_time (fallback to end_time date if needed)
    try:
        if duration_seconds and duration_seconds > 0:
            minutes = Decimal(str(duration_seconds)) / Decimal('60')
            # decide which date to attribute sleep to: prefer start_time.date(), fallback to end_time.date()
            date_for_summary = None
            try:
                if start_time:
                    date_for_summary = (start_time.date() if hasattr(start_time, 'date') else None)
                if not date_for_summary and end_time:
                    date_for_summary = (end_time.date() if hasattr(end_time, 'date') else None)
            except Exception:
                date_for_summary = None

            if date_for_summary:
                summary = _get_or_create_summary(record.profile, date_for_summary)
                # atomic increment of sleep minutes total
                DailyHealthSummary.objects.filter(pk=summary.pk).update(sleep_minutes_total=F('sleep_minutes_total') + minutes)
    except Exception:
        logger.exception("Failed to update DailyHealthSummary sleep total for record %s", record.record_id)


def _handle_exercise(record: HealthConnectRawData):
    """
    Normalize exercise / activity sessions.
    """
    data = record.data or {}
    activity_type = data.get('activityType') or data.get('activity') or data.get('type') or 'exercise'
    calories = None
    distance_m = None
    avg_hr = None
    power = None

    energy = data.get('energy') or {}
    if isinstance(energy, dict):
        calories = energy.get('inCalories') or energy.get('inKilocalories') or energy.get('inKcal')

    distance = data.get('distance') or {}
    if isinstance(distance, dict):
        distance_m = distance.get('inMeters') or distance.get('meters')

    avg_hr = data.get('averageHeartRate') or data.get('avgHeartRate') or data.get('average_heart_rate')
    power = data.get('totalPower') or data.get('power')

    ExerciseSession.objects.update_or_create(
        source_id=record.record_id,
        defaults={
            'user': record.profile,
            'source': 'healthconnect',
            'activity_type': activity_type,
            'start_time': record.start_time,
            'end_time': record.end_time,
            'calories_burned': _to_decimal(calories) if calories else None,
            'distance_meters': _to_decimal(distance_m) if distance_m else None,
            'average_heart_rate': int(avg_hr) if avg_hr else None,
            'total_power': _to_decimal(power) if power else None,
            'data': data,
        }
    )

    # Optionally increment daily summary calories if calories present
    if calories:
        calories_dec = _to_decimal(calories)
        summary = _get_or_create_summary(record.profile, record.start_time.date())
        DailyHealthSummary.objects.filter(pk=summary.pk).update(active_calories_total=F('active_calories_total') + calories_dec)


def _handle_active_calories(record: HealthConnectRawData):
    """
    Handles activeCaloriesBurned / totalCaloriesBurned entries.
    Extracts kcal (prefer inKilocalories/inKcal), otherwise converts inCalories -> kcal by dividing by 1000,
    writes a MetricSample for traceability and increments DailyHealthSummary.calories_total.
    """
    data = record.data or {}
    energy = data.get('energy') or {}
    kcal = None
    if isinstance(energy, dict):
        kcal = energy.get('inKilocalories') or energy.get('inKcal') or energy.get('inKilocalorie')
        if kcal is None and ('inCalories' in energy or energy.get('inCalories') is not None):
            raw = energy.get('inCalories')
            try:
                kcal = Decimal(str(raw)) / Decimal('1000')
            except Exception:
                kcal = raw
    # Fallback top-level
    if kcal is None:
        kcal = data.get('calories') or data.get('kcal') or data.get('inKilocalories')

    if kcal is None:
        return

    kcal_dec = _to_decimal(kcal, Decimal('0'))

    # Create a metric sample for active calories
    try:
        MetricSample.objects.create(
            user=record.profile,
            source='healthconnect',
            source_id=record.record_id,
            datetime=record.start_time or timezone.now(),
            metric=record.method or 'activeCaloriesBurned',
            value=kcal_dec,
            unit='kcal',
            data=data,
        )
    except Exception:
        logger.exception("Failed to create MetricSample for active calories %s", record.record_id)

    # Update daily summary with active calories
    try:
        summary = _get_or_create_summary(record.profile, record.start_time.date())
        DailyHealthSummary.objects.filter(pk=summary.pk).update(active_calories_total=F('active_calories_total') + kcal_dec)
    except Exception:
        logger.exception("Failed to update DailyHealthSummary for active calories %s", record.record_id)


def _handle_blood_pressure(record: HealthConnectRawData):
    """
    Normalize blood pressure readings.
    """
    data = record.data or {}
    systolic = None
    diastolic = None

    bp = data.get('bloodPressure') or data.get('value') or data
    if isinstance(bp, dict):
        systolic = bp.get('systolic') or bp.get('systolicMillimetersOfMercury') or bp.get('systolicMmHg')
        diastolic = bp.get('diastolic') or bp.get('diastolicMillimetersOfMercury') or bp.get('diastolicMmHg')

    try:
        if systolic is None:
            systolic = data.get('systolic')
        if diastolic is None:
            diastolic = data.get('diastolic')
        if systolic is None or diastolic is None:
            return

        BloodPressure.objects.update_or_create(
            source_id=record.record_id,
            defaults={
                'user': record.profile,
                'source': 'healthconnect',
                'datetime': record.start_time,
                'systolic': int(systolic),
                'diastolic': int(diastolic),
                'data': data,
            }
        )
    except (TypeError, ValueError):
        logger.exception("Invalid blood pressure values for record %s: %s", record.record_id, data)


def _handle_body_composition(record: HealthConnectRawData):
    """
    Normalize body composition (body fat, lean mass, bone mass).
    """
    data = record.data or {}
    bf = None
    lean_kg = None
    bone_kg = None
    visceral = None

    bf = (data.get('bodyFat') or {}).get('inPercent') if isinstance(data.get('bodyFat'), dict) else data.get('bodyFat') or data.get('body_fat_percent')
    lean = (data.get('leanMass') or {}).get('inKilograms') if isinstance(data.get('leanMass'), dict) else data.get('leanMass') or data.get('lean_mass_kg')
    bone = (data.get('boneMass') or {}).get('inKilograms') if isinstance(data.get('boneMass'), dict) else data.get('boneMass') or data.get('bone_mass_kg')
    visceral = data.get('visceralFatIndex') or data.get('visceralFat')

    BodyComposition.objects.update_or_create(
        source_id=record.record_id,
        defaults={
            'user': record.profile,
            'source': 'healthconnect',
            'datetime': record.start_time,
            'body_fat_percent': _to_decimal(bf) if bf is not None else None,
            'lean_mass_kg': _to_decimal(lean) if lean is not None else None,
            'bone_mass_kg': _to_decimal(bone) if bone is not None else None,
            'visceral_fat_index': _to_decimal(visceral) if visceral is not None else None,
            'data': data,
        }
    )


def _handle_menstruation(record: HealthConnectRawData):
    """
    Normalize menstruation / period entries. Health Connect may provide start/end windows.
    """
    data = record.data or {}
    start = data.get('startDate') or data.get('start') or data.get('start_date')
    end = data.get('endDate') or data.get('end') or data.get('end_date')
    avg_flow = data.get('flow') or data.get('averageFlow') or None
    symptoms = data.get('symptoms') or None

    if not start:
        # if there's no start date, attempt to support date-only start_time
        start = record.start_time.date() if record.start_time else None

    if not start:
        return

    try:
        # create/update using strings/dates; Django will coerce ISO strings when assigning to DateField if provided via ORM
        MenstruationPeriod.objects.update_or_create(
            source_id=record.record_id,
            defaults={
                'user': record.profile,
                'source': 'healthconnect',
                'start_date': start,
                'end_date': end,
                'average_flow': avg_flow,
                'symptoms': symptoms,
                'data': data,
            }
        )
    except Exception:
        logger.exception("Failed to upsert menstruation record %s", record.record_id)


def _handle_metric(record: HealthConnectRawData):
    """
    Generic handler to store single-value metrics as MetricSample.
    This covers heartRate, oxygenSaturation, vo2Max, respiratoryRate, etc.
    """
    data = record.data or {}
    # Try several common field names
    value = data.get('value') or data.get('avg') or data.get('average') or data.get('inBeatsPerMinute') or data.get('inPercent') or data.get('inMilliliters')
    unit = data.get('unit') or data.get('uom') or None

    # If there's an 'samples' array with a single value, prefer that
    if value is None and isinstance(data.get('samples'), list) and data['samples']:
        sample = data['samples'][0]
        value = sample.get('value') if isinstance(sample, dict) else sample

    if value is None:
        # as last resort look for top-level numeric fields
        for k, v in data.items():
            if isinstance(v, (int, float, Decimal, str)):
                try:
                    Decimal(str(v))
                    value = v
                    break
                except Exception:
                    continue

    if value is None:
        return

    MetricSample.objects.create(
        user=record.profile,
        source='healthconnect',
        source_id=record.record_id,
        datetime=record.start_time or timezone.now(),
        metric=record.method,
        value=_to_decimal(value),
        unit=unit,
        data=data,
    )


def _handle_fallback_metric(record: HealthConnectRawData):
    """
    Default fallback: attempt to store as a MetricSample so we capture many single-value types
    without needing an explicit model for each.
    """
    _handle_metric(record)