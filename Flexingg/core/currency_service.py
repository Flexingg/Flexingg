from decimal import Decimal, InvalidOperation, getcontext
from typing import Tuple
from datetime import datetime as _dt_datetime, date as _dt_date

# Set a sensible default precision for currency calculations
getcontext().prec = 9


def _to_decimal(value) -> Decimal:
    """
    Helper to coerce numeric inputs to Decimal safely.
    """
    try:
        return Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(0)


def calculate_cardio_coins(calories, multiplier=1.0) -> Decimal:
    """
    Calculate CardioCoins from calories.
    Formula: calories * 1.0 * multiplier
    Returns a Decimal.
    """
    c = _to_decimal(calories)
    m = _to_decimal(multiplier)
    result = c * Decimal(1) * m
    # Prevent negatives
    if result < 0:
        return Decimal(0)
    return result


def calculate_gym_gems(volume_lbs, bodyweight_lbs=200.0, multiplier=1.0) -> Decimal:
    """
    Calculate GymGems from lifted volume normalized by bodyweight.
    Formula: volume_lbs * (1.0 / bodyweight_lbs) * multiplier
    Returns a Decimal.
    """
    v = _to_decimal(volume_lbs)
    bw = _to_decimal(bodyweight_lbs)
    m = _to_decimal(multiplier)
    if bw <= 0:
        # Defensive fallback to 200 if invalid bodyweight provided
        bw = Decimal(200)
    result = v * (Decimal(1) / bw) * m
    if result < 0:
        return Decimal(0)
    return result


def calculate_xp_from_currencies(cardio_coins, gym_gems) -> int:
    """
    Calculate XP from currencies using the formula:
    XP = (cardio_coins * 1) + (gym_gems * 2)
    Returns an integer XP value (rounded down).
    """
    cc = _to_decimal(cardio_coins)
    gg = _to_decimal(gym_gems)
    xp_decimal = (cc * Decimal(1)) + (gg * Decimal(2))
    if xp_decimal <= 0:
        return 0
    # Return integer XP (floor)
    return int(xp_decimal.quantize(Decimal('1')))


# --- Higher-level helpers that interact with Django models --- #
def award_currencies_and_xp(user, cardio_coins_amount, gym_gems_amount, garmin_activity=None, activity_timestamp=None):
    """
    Create Transaction records for CardioCoins, GymGems, and XP, update user balances and XP.
    This centralizes currency awarding and ensures Transaction.xp_awarded is recorded.

    New behavior: if an activity timestamp (or a timestamp extractable from garmin_activity)
    exists and is before the user's date_joined, the function will return without awarding
    any currency/xp.
    """
    from .models import Transaction
    from datetime import datetime as _dt_datetime, date as _dt_date

    def _get_activity_time(obj):
        if obj is None:
            return None
        # If the object is already a datetime/date/str or a callable (e.g., timezone.now),
        # return it directly and let the normalizer handle it. This prevents accidentally
        # returning attribute objects (methods) from getattr() calls on unexpected types.
        from datetime import datetime as _local_dt, date as _local_date
        try:
            if isinstance(obj, (_local_dt, _local_date, str)) or callable(obj):
                return obj
        except Exception:
            # Fall through to attribute/dict extraction
            pass
        try:
            # model-like objects: common datetime fields
            for attr in ('start_time', 'timestamp', 'created_at', 'begin_time'):
                val = getattr(obj, attr, None)
                if val:
                    return val
            # dict-like objects
            if isinstance(obj, dict):
                for key in ('start_time', 'timestamp', 'created_at', 'begin_time'):
                    if obj.get(key):
                        return obj.get(key)
        except Exception:
            return None
        return None

    def _normalize_to_datetime(val):
        """
        Normalize val to a datetime.datetime when possible.
        - If val is callable, call it with no args and use its return value.
        - If val is a datetime or date, convert/return a datetime.
        - If val is an ISO string, attempt to parse with fromisoformat (handle trailing 'Z').
        Returns a datetime or None.
        """
        if val is None:
            return None
        try:
            # If it's callable (e.g., someone accidentally passed timezone.now), call it.
            if callable(val):
                try:
                    val = val()
                except Exception:
                    return None
            # datetime already
            if isinstance(val, _dt_datetime):
                return val
            # date -> convert to datetime at midnight
            if isinstance(val, _dt_date):
                try:
                    return _dt_datetime.combine(val, _dt_datetime.min.time())
                except Exception:
                    return None
            # string -> try ISO parse
            if isinstance(val, str):
                try:
                    s = val
                    if 'Z' in s:
                        s = s.replace('Z', '+00:00')
                    return _dt_datetime.fromisoformat(s)
                except Exception:
                    return None
        except Exception:
            return None
        return None

    # Prefer explicit activity_timestamp param, fall back to garmin_activity
    raw_activity_time = _get_activity_time(activity_timestamp) or _get_activity_time(garmin_activity)
    activity_time = _normalize_to_datetime(raw_activity_time)

    # Normalize user's date_joined as well and guard comparisons
    raw_joined = getattr(user, 'date_joined', None)
    joined_time = _normalize_to_datetime(raw_joined)

    # If both normalized datetimes exist, do not award for pre-join activities
    if activity_time and joined_time:
        try:
            # Prefer comparing epoch timestamps to avoid TypeError when objects are unusual.
            act_epoch = None
            join_epoch = None
            if hasattr(activity_time, 'timestamp'):
                try:
                    act_epoch = float(activity_time.timestamp())
                except Exception:
                    act_epoch = None
            elif isinstance(activity_time, (int, float)):
                act_epoch = float(activity_time)

            if hasattr(joined_time, 'timestamp'):
                try:
                    join_epoch = float(joined_time.timestamp())
                except Exception:
                    join_epoch = None
            elif isinstance(joined_time, (int, float)):
                join_epoch = float(joined_time)

            if act_epoch is not None and join_epoch is not None:
                if act_epoch < join_epoch:
                    return {'cardio_coins': 0, 'gym_gems': 0, 'xp_awarded': 0}
            else:
                # Fallback: try direct comparison if both are datetimes
                try:
                    if activity_time < joined_time:
                        return {'cardio_coins': 0, 'gym_gems': 0, 'xp_awarded': 0}
                except Exception:
                    # If comparison fails for any reason, fall through and allow awarding (defensive)
                    pass
        except Exception:
            # Defensive: do not block awarding if unexpected errors occur during normalization/comparison
            pass

    try:
        # Normalize to Decimals/ints
        cc = _to_decimal(cardio_coins_amount)
        gg = _to_decimal(gym_gems_amount)

        # Award CardioCoins
        if cc > 0:
            Transaction.objects.create(
                user=user,
                currency_type='cardio_coins',
                amount=cc,
                garmin_activity=garmin_activity,
            )
            user.cardio_coins = (user.cardio_coins or 0) + cc
        # Award GymGems
        if gg > 0:
            Transaction.objects.create(
                user=user,
                currency_type='gym_gems',
                amount=gg,
                garmin_activity=garmin_activity,
            )
            user.gym_gems = (user.gym_gems or 0) + gg

        # Calculate and award XP
        xp = calculate_xp_from_currencies(cc, gg)
        if xp > 0:
            # Store XP as a separate transaction with amount 0 and xp_awarded set
            Transaction.objects.create(
                user=user,
                currency_type='xp',
                amount=Decimal(0),
                xp_awarded=int(xp),
                garmin_activity=garmin_activity,
            )
            user.xp = (user.xp or 0) + int(xp)

        # Persist user updates
        user.save()
        return {
            'cardio_coins': float(cc),
            'gym_gems': float(gg),
            'xp_awarded': int(xp)
        }
    except Exception as e:
        # Avoid importing logging at module import time; raise for caller to handle logging if needed
        raise


# --- Level helpers (require Level model to exist) --- #
def calculate_user_level(total_xp: int) -> int:
    """
    Determine the user's level based on total cumulative XP using Level model.
    Returns the highest level_number where total_xp >= xp_required.
    Falls back to 1 if Level table is empty or on error.
    """
    try:
        from .models import Level
        levels = Level.objects.order_by('level_number').all()
        if not levels:
            return 1
        current_level = 1
        for lvl in levels:
            if total_xp >= lvl.xp_required:
                current_level = lvl.level_number
            else:
                break
        return current_level
    except Exception:
        return 1


def get_next_level_xp(current_level: int) -> int:
    """
    Return the xp_required for the next level (cumulative XP required to reach next level).
    If next level not found, return None.
    """
    try:
        from .models import Level
        next_level = Level.objects.filter(level_number=current_level + 1).first()
        return next_level.xp_required if next_level else None
    except Exception:
        return None


def get_level_progress_percentage(current_xp: int, current_level: int) -> float:
    """
    Compute percentage progress toward next level.
    Uses cumulative xp_required values from Level model.
    If next level not defined, returns 100.0.
    """
    try:
        from .models import Level
        current_lvl_obj = Level.objects.filter(level_number=current_level).first()
        next_lvl_obj = Level.objects.filter(level_number=current_level + 1).first()
        if not current_lvl_obj or not next_lvl_obj:
            return 100.0
        base = current_lvl_obj.xp_required
        top = next_lvl_obj.xp_required
        if top <= base:
            return 100.0
        progress = (current_xp - base) / (top - base)
        progress = max(0.0, min(1.0, progress))
        return float(progress * 100.0)
    except Exception:
        return 0.0