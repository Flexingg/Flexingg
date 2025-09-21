#!/usr/bin/env python3
"""
Test script to debug nutrition data parsing from Health Connect
"""

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

print('Testing current parsing logic:')
print('Raw data keys:', list(test_data.keys()))
print()

# Current parsing logic from tasks.py
calories = test_data.get('energy', {}).get('inKilocalories') if isinstance(test_data.get('energy'), dict) else None
protein_grams = test_data.get('protein', {}).get('inGrams') if isinstance(test_data.get('protein'), dict) else None
fat_grams = test_data.get('totalFat', {}).get('inGrams') if isinstance(test_data.get('totalFat'), dict) else None
carbs_grams = test_data.get('totalCarbohydrate', {}).get('inGrams') if isinstance(test_data.get('totalCarbohydrate'), dict) else None

print('Parsed values:')
print(f'calories: {calories} (type: {type(calories)})')
print(f'protein_grams: {protein_grams} (type: {type(protein_grams)})')
print(f'fat_grams: {fat_grams} (type: {type(fat_grams)})')
print(f'carbs_grams: {carbs_grams} (type: {type(carbs_grams)})')
print()

# Convert to Decimal for database storage
try:
    calories = float(calories) if calories is not None else None
    protein_grams = float(protein_grams) if protein_grams is not None else None
    fat_grams = float(fat_grams) if fat_grams is not None else None
    carbs_grams = float(carbs_grams) if carbs_grams is not None else None
    print('After float conversion:')
    print(f'calories: {calories}')
    print(f'protein_grams: {protein_grams}')
    print(f'fat_grams: {fat_grams}')
    print(f'carbs_grams: {carbs_grams}')
    print()
    print('SUCCESS: All values parsed correctly!')
except (ValueError, TypeError) as e:
    print(f'Error in conversion: {e}')

# Test with the actual JSON structure from the user
print('\n' + '='*50)
print('Testing with full JSON structure:')
full_json = {
    "app_source": "com.sbs.diet",
    "healthconnect_data": {
        "id": "dbb1ef6e-3c04-4551-83c9-nbb n",
        "_id": "dbb1ef6e-3c04-4551-83c9-8283af2f2422",
        "app": "com.sbs.diet",
        "end": "2025-09-18T15:36:58Z",
        "data": test_data,
        "name": None,
        "start": "2025-09-18T15:35:58Z"
    }
}

# The data field contains the nutrition data
nutrition_data = full_json["healthconnect_data"]["data"]
print('Nutrition data keys:', list(nutrition_data.keys()))
print()

# Test parsing from the data field
calories = nutrition_data.get('energy', {}).get('inKilocalories') if isinstance(nutrition_data.get('energy'), dict) else None
protein_grams = nutrition_data.get('protein', {}).get('inGrams') if isinstance(nutrition_data.get('protein'), dict) else None
fat_grams = nutrition_data.get('totalFat', {}).get('inGrams') if isinstance(nutrition_data.get('totalFat'), dict) else None
carbs_grams = nutrition_data.get('totalCarbohydrate', {}).get('inGrams') if isinstance(nutrition_data.get('totalCarbohydrate'), dict) else None

print('Parsed from full JSON:')
print(f'calories: {calories}')
print(f'protein_grams: {protein_grams}')
print(f'fat_grams: {fat_grams}')
print(f'carbs_grams: {carbs_grams}')