# Plan for Importing Liftosaur Workout Data into Django Models

## 1. Analysis of Current State
### Current Models (from Flexingg/liftosaur/models.py)
- **Exercise**: Basic exercise types (id, name). Maps to JSON's exercise objects (e.g., {"equipment": "barbell", "id": "squat"}).
- **UserExerciseStat**: User-specific 1RM data (user, exercise, rm1_value, rm1_unit). Can populate from JSON's "exerciseData" (e.g., "squat_barbell": {"rm1": {"value": 195, "unit": "lb"}}).
- **Workout**: Workout sessions (id, user, timestamp, name, gym_id, program_id). Maps to JSON's "history" array items (e.g., "id", "user" via email/user_id, "timestamp" from "date", "programId").
- **WorkoutExercise**: Exercises in a workout (workout, exercise_name, note, timestamp). Partially maps to JSON's "entries" (programExerciseId, exercise, notes, state.timestamp), but lacks set-level details.
- **BodyMeasurement**: Bodyweight/measurements (user, type, value, unit, timestamp). Directly maps to JSON's "currentBodyweight" and potentially history if more measurements exist.
- **Program**: Stores full program JSON (user, external_id, name, data). Can store JSON's "programs" array items.

### JSON Structure (from REFERENCE ONLY/liftosaur_data (small).json)
- **storage.settings**: User prefs (currentGymId, currentBodyweight, equipment configs, exerciseData for 1RMs).
- **storage.history**: Array of workout records. Each record has:
  - "id", "programId", "date" (timestamp), "dayName", "entries" (array of exercises).
  - Each entry: "programExerciseId", "exercise" ({"equipment", "id"}), "notes", "state" (successes, failures, weights), "sets" (array: reps, weight, completedReps, completedWeight, timestamp, isCompleted, isAmrap, logRpe, completedRpe), "warmupSets" (similar but simpler).
- **storage.programs**: Array of programs with "id", "name", "days" (exercises with ids, states), "weeks".
- **storage.stats**: Empty in sample, but could have aggregates.
- Key goal: Import every rep means storing per-set data (completedReps, completedWeight, etc.) for analysis (e.g., volume, PRs).

### Gaps Identified
- No model for individual sets/reps. WorkoutExercise only captures exercise-level summary; can't store granular set data like reps, weights, RPE, timestamps per set.
- No distinction between working sets and warmup sets.
- Program model stores raw JSON, but for full integration, may need parsed ProgramDay, ProgramExercise models.
- No import mechanism (e.g., Celery task) to parse JSON and create DB instances.
- User linking: JSON has "email" and "user_id"; map to UserProfile via email or liftosaur_user_id field.
- Equipment/Gym: JSON has detailed equipment; current models don't store this, but could add if needed for calculations.

## 2. Proposed Changes
### Model Updates/Additions (in liftosaur/models.py)
- **New: WorkoutSet** (linked to WorkoutExercise):
  - id (UUID)
  - workout_exercise (ForeignKey to WorkoutExercise)
  - set_order (IntegerField)  # e.g., 1,2,3 for working sets; negative for warmups (e.g., -1,-2)
  - reps (FloatField, null=True)  # Planned reps
  - weight_value (FloatField, null=True)
  - weight_unit (CharField, max_length=10, default='lb')
  - completed_reps (IntegerField, default=0)
  - completed_weight_value (FloatField, null=True)
  - completed_weight_unit (CharField, max_length=10, null=True)
  - rpe (IntegerField, null=True)  # Planned RPE
  - completed_rpe (IntegerField, null=True)
  - is_amrap (BooleanField, default=False)
  - is_completed (BooleanField, default=False)
  - timestamp (DateTimeField, null=True)  # Set completion time
  - is_warmup (BooleanField, default=False)
  - notes (TextField, blank=True)
  - Meta: ordering = ['set_order']

- **Update WorkoutExercise**:
  - Add: successes (IntegerField, default=0), failures (IntegerField, default=0)  # From entry.state
  - Add: planned_weight_value/unit, reps_scheme (from program exercise state)

- **Update Program**:
  - Ensure data JSONField captures full program structure. Optionally add parsed models like ProgramDay, ProgramExercise if needed for querying.

- **Migration**: After model changes, create migration (e.g., python manage.py makemigrations liftosaur).

### Import Logic
- **Celery Task** (in liftosaur/tasks.py): def import_liftosaur_data(user_profile, json_data):
  - Parse JSON: storage['history'] for workouts.
  - For each history item:
    - Create/update Workout (match by id or timestamp/user).
    - For each entry:
      - Get/create Exercise (from exercise.id + equipment).
      - Create WorkoutExercise (exercise_name=exercise.id + '_' + equipment, note=notes, timestamp=entry timestamp).
      - For each set in sets[]: Create WorkoutSet (workout_exercise, set_order=i+1, reps=set.reps, weight=set.weight, completed_reps=set.completedReps, etc., is_warmup=False).
      - For each warmup in warmupSets[]: Create WorkoutSet (..., is_warmup=True, no RPE/amrap usually).
    - Update UserExerciseStat from exerciseData.
    - Create BodyMeasurement from currentBodyweight.
    - Store programs in Program model (external_id=program.id, data=program JSON).
  - Handle units (lb/kg), timestamps (ISO to DateTime).
  - Error handling: Skip invalid data, log issues.
  - Trigger: Via view (upload JSON) or admin command.

- **View/Task Integration** (liftosaur/views.py/tasks.py):
  - Add view for JSON upload (POST to /liftosaur/import/, parse file, call task).
  - Async via Celery for large imports.

## 3. Execution Steps
1. Update models.py with new WorkoutSet model and fields.
2. Run makemigrations && migrate.
3. Implement import task in tasks.py.
4. Add import view/URL.
5. Test with sample JSON: Create test user, run task, verify DB entries (e.g., query WorkoutSets for a workout).
6. Edge cases: Mixed units, incomplete sets, multiple programs.
7. Performance: For large JSON, batch creates (bulk_create).

## 4. Potential Enhancements
- Calculate derived stats (volume = sum(weight * reps per set)) in model methods.
- Integrate with core (e.g., update UserProfile stats from imports).
- Validation: Ensure JSON schema matches expected structure.

This plan ensures full rep-level data import. Estimated effort: 2-4 hours for models/task, plus testing.