from decimal import Decimal, InvalidOperation, getcontext
from typing import Tuple

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
def award_currencies_and_xp(user, cardio_coins_amount, gym_gems_amount, garmin_activity=None):
    """
    Create Transaction records for CardioCoins, GymGems, and XP, update user balances and XP.
    This centralizes currency awarding and ensures Transaction.xp_awarded is recorded.
    """
    from .models import Transaction
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