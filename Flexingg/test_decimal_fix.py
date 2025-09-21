#!/usr/bin/env python3
"""
Test script to verify the Decimal fix for nutrition data parsing
"""

from decimal import Decimal

# Test data from the user
test_data = {
    "energy": {
        "inJoules": 2410970.587579969,
        "inCalories": 576235.7999999999,
        "inKilojoules": 2410.9705875799687,
        "inKilocalories": 576.2357999999999
    },
    "protein": {
        "inGrams": 21.0672,
        "inOunces": 0.7431236930995657,
        "inPounds": 0.04644522569901253,
        "inKilograms": 0.0210672,
        "inMicrograms": 21067200,
        "inMilligrams": 21067.2
    },
    "totalFat": {
        "inGrams": 20.515320000000003,
        "inOunces": 0.7236566968329624,
        "inPounds": 0.04522853856646663,
        "inKilograms": 0.020515320000000004,
        "inMicrograms": 20515320.000000004,
        "inMilligrams": 20515.320000000003
    },
    "totalCarbohydrate": {
        "inGrams": 75.46644,
        "inOunces": 2.6620006264656335,
        "inPounds": 0.16637502081439334,
        "inKilograms": 0.07546644000000001,
        "inMicrograms": 75466440.00000001,
        "inMilligrams": 75466.44
    },
    "name": None
}

print("Testing Decimal conversion fix:")
print("Raw data keys:", list(test_data.keys()))
print()

# Current parsing logic from tasks.py (with the fix)
calories = test_data.get('energy', {}).get('inKilocalories') if isinstance(test_data.get('energy'), dict) else None
protein_grams = test_data.get('protein', {}).get('inGrams') if isinstance(test_data.get('protein'), dict) else None
fat_grams = test_data.get('totalFat', {}).get('inGrams') if isinstance(test_data.get('totalFat'), dict) else None
carbs_grams = test_data.get('totalCarbohydrate', {}).get('inGrams') if isinstance(test_data.get('totalCarbohydrate'), dict) else None

print("Parsed values:")
print(f"  calories: {calories} (type: {type(calories)})")
print(f"  protein_grams: {protein_grams} (type: {type(protein_grams)})")
print(f"  fat_grams: {fat_grams} (type: {type(fat_grams)})")
print(f"  carbs_grams: {carbs_grams} (type: {type(carbs_grams)})")
print()

# Test the OLD conversion logic (float)
print("OLD conversion logic (float):")
try:
    calories_float = float(calories) if calories is not None else None
    protein_grams_float = float(protein_grams) if protein_grams is not None else None
    fat_grams_float = float(fat_grams) if fat_grams is not None else None
    carbs_grams_float = float(carbs_grams) if carbs_grams is not None else None
    print(f"  calories: {calories_float} (type: {type(calories_float)})")
    print(f"  protein_grams: {protein_grams_float} (type: {type(protein_grams_float)})")
    print(f"  fat_grams: {fat_grams_float} (type: {type(fat_grams_float)})")
    print(f"  carbs_grams: {carbs_grams_float} (type: {type(carbs_grams_float)})")
    print("  SUCCESS: Float conversion works")
except (ValueError, TypeError) as e:
    print(f"  ERROR in float conversion: {e}")

print()

# Test the NEW conversion logic (Decimal)
print("NEW conversion logic (Decimal):")
try:
    calories_decimal = Decimal(str(calories)) if calories is not None else None
    protein_grams_decimal = Decimal(str(protein_grams)) if protein_grams is not None else None
    fat_grams_decimal = Decimal(str(fat_grams)) if fat_grams is not None else None
    carbs_grams_decimal = Decimal(str(carbs_grams)) if carbs_grams is not None else None
    print(f"  calories: {calories_decimal} (type: {type(calories_decimal)})")
    print(f"  protein_grams: {protein_grams_decimal} (type: {type(protein_grams_decimal)})")
    print(f"  fat_grams: {fat_grams_decimal} (type: {type(fat_grams_decimal)})")
    print(f"  carbs_grams: {carbs_grams_decimal} (type: {type(carbs_grams_decimal)})")
    print("  SUCCESS: Decimal conversion works")
except (ValueError, TypeError, Exception) as e:
    print(f"  ERROR in Decimal conversion: {e}")

print()
print("Comparison:")
print(f"  Float calories: {calories_float}")
print(f"  Decimal calories: {calories_decimal}")
print(f"  Are they equal? {calories_float == float(calories_decimal) if calories_decimal else 'N/A'}")

print()
print("✅ FIX SUMMARY:")
print("  - Added 'from decimal import Decimal' to imports")
print("  - Changed float() conversion to Decimal(str()) conversion")
print("  - This ensures proper Decimal objects for DecimalField database storage")
print("  - The parsing logic itself was already correct")