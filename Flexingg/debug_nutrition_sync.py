#!/usr/bin/env python3
"""
Debug script to check nutrition data sync and normalization
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Flexingg.settings')
django.setup()

from core.models import NutritionEntry, UserProfile
from healthconnect.models import HealthConnectData
import json

def debug_nutrition_sync():
    print("=== NUTRITION DATA DEBUG ===")
    print()

    # Check if there are any users
    users = UserProfile.objects.all()
    print(f"Total users: {users.count()}")

    if users.count() == 0:
        print("No users found. Please create a user first.")
        return

    user = users.first()
    print(f"Checking data for user: {user.username}")
    print()

    # Check HealthConnectData records
    hc_records = HealthConnectData.objects.filter(profile=user, method='nutrition')
    print(f"Health Connect nutrition records: {hc_records.count()}")

    if hc_records.count() == 0:
        print("No nutrition records found in HealthConnectData.")
        print("This suggests the sync hasn't happened or no nutrition data was received.")
        return

    print("\n=== HEALTH CONNECT NUTRITION RECORDS ===")
    for record in hc_records[:3]:  # Show first 3 records
        print(f"Record ID: {record.record_id}")
        print(f"Start time: {record.start_time}")
        print(f"App source: {record.app_source}")
        print(f"Data keys: {list(record.data.keys()) if record.data else 'No data'}")

        if record.data:
            # Check if nutrition data is in the data field
            if 'energy' in record.data:
                print(f"  Energy: {record.data['energy'].get('inCalories', 'N/A')} kcal")
            if 'protein' in record.data:
                print(f"  Protein: {record.data['protein'].get('inGrams', 'N/A')} g")
            if 'totalFat' in record.data:
                print(f"  Fat: {record.data['totalFat'].get('inGrams', 'N/A')} g")
            if 'totalCarbohydrate' in record.data:
                print(f"  Carbs: {record.data['totalCarbohydrate'].get('inGrams', 'N/A')} g")

        print()

    # Check NutritionEntry records
    nutrition_entries = NutritionEntry.objects.filter(user=user)
    print(f"\n=== NUTRITION ENTRY RECORDS ===")
    print(f"Total NutritionEntry records: {nutrition_entries.count()}")

    if nutrition_entries.count() == 0:
        print("No NutritionEntry records found.")
        print("This suggests the normalization task hasn't run or failed.")
    else:
        print("\nSample NutritionEntry records:")
        for entry in nutrition_entries[:3]:  # Show first 3 records
            print(f"Food: {entry.food_name}")
            print(f"Calories: {entry.calories}")
            print(f"Protein: {entry.protein_grams}g")
            print(f"Fat: {entry.fat_grams}g")
            print(f"Carbs: {entry.carbs_grams}g")
            print(f"Source: {entry.source}")
            print(f"Source ID: {entry.source_id}")
            print()

    # Check if there are any records that should have been normalized but weren't
    print("=== CHECKING FOR UNNORMALIZED RECORDS ===")
    unnormalized_count = 0
    for record in hc_records:
        if not NutritionEntry.objects.filter(
            user=user,
            source='healthconnect',
            source_id=record.record_id
        ).exists():
            unnormalized_count += 1
            if unnormalized_count <= 3:  # Show first 3 unnormalized records
                print(f"Unnormalized record: {record.record_id}")
                print(f"  Data: {record.data.get('name', 'No name')}")
                print(f"  Energy: {record.data.get('energy', {}).get('inKilocalories', 'N/A')}")

    print(f"\nTotal unnormalized records: {unnormalized_count}")

    if unnormalized_count > 0:
        print("\n=== TESTING NORMALIZATION ON ONE RECORD ===")
        test_record = hc_records.filter(
            ~NutritionEntry.objects.filter(
                user=user,
                source='healthconnect',
                source_id__in=hc_records.values('record_id')
            )
        ).first()

        if test_record:
            print(f"Testing normalization on record: {test_record.record_id}")
            print(f"Data: {json.dumps(test_record.data, indent=2)}")

            # Test the parsing logic
            data = test_record.data
            calories = data.get('energy', {}).get('inCalories') if isinstance(data.get('energy'), dict) else None
            protein_grams = data.get('protein', {}).get('inGrams') if isinstance(data.get('protein'), dict) else None
            fat_grams = data.get('totalFat', {}).get('inGrams') if isinstance(data.get('totalFat'), dict) else None
            carbs_grams = data.get('totalCarbohydrate', {}).get('inGrams') if isinstance(data.get('totalCarbohydrate'), dict) else None

            print("Parsed values:")
            print(f"  Calories: {calories}")
            print(f"  Protein: {protein_grams}")
            print(f"  Fat: {fat_grams}")
            print(f"  Carbs: {carbs_grams}")

            # Test conversion to float
            try:
                calories = float(calories) if calories is not None else None
                protein_grams = float(protein_grams) if protein_grams is not None else None
                fat_grams = float(fat_grams) if fat_grams is not None else None
                carbs_grams = float(carbs_grams) if carbs_grams is not None else None
                print("After conversion:")
                print(f"  Calories: {calories}")
                print(f"  Protein: {protein_grams}")
                print(f"  Fat: {fat_grams}")
                print(f"  Carbs: {carbs_grams}")
                print("  SUCCESS: Values can be converted!")
            except Exception as e:
                print(f"  ERROR in conversion: {e}")

if __name__ == "__main__":
    debug_nutrition_sync()