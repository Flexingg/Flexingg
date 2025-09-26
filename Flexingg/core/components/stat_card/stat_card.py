from django_components import component
from django.utils import timezone
from core.models import Workout, BodyWeight

@component.register("stat_card")
class StatCard(component.Component):
    template_name = "stat_card/template.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs) or {}
        context['todays_total_calories'] = kwargs.get('todays_total_calories', 0)
        context['todays_steps'] = kwargs.get('todays_steps', 0)
        context['todays_consumed_calories'] = kwargs.get('todays_consumed_calories', 0)
        # Compute today's lifting volume (in thousands of lbs, "k") if not supplied by caller.
        if 'todays_lifting_volume_k' in kwargs:
            context['todays_lifting_volume_k'] = kwargs.get('todays_lifting_volume_k', 0)
        else:
            user = kwargs.get('user') or getattr(kwargs.get('request'), 'user', None)
            target_date = kwargs.get('date') or timezone.now().date()
            vol_k = 0.0
            if user and hasattr(user, 'is_authenticated') and user.is_authenticated:
                try:
                    workouts = Workout.objects.filter(user=user, start_time__date=target_date)
                    total_lbs = 0.0
                    for w in workouts:
                        try:
                            total_lbs += float(w.get_total_volume(unit='lb') or 0)
                        except Exception:
                            # ignore single-workout parse errors
                            pass
                    vol_k = total_lbs / 1000.0
                except Exception:
                    vol_k = 0.0
            context['todays_lifting_volume_k'] = vol_k
        context['todays_water_ounces'] = kwargs.get('todays_water_ounces', 0)
        context['fitness_summary'] = kwargs.get('fitness_summary', {})

        # Bodyweight: try latest synced weight for the target date, fall back to profile.bodyweight_lbs, otherwise None
        # Use timezone-aware filtering via __date lookup (DB stores aware datetimes)
        try:
            user = kwargs.get('user') or getattr(kwargs.get('request'), 'user', None)
            target_date = kwargs.get('date') or timezone.now().date()
            todays_bodyweight = None
            if user and hasattr(user, 'is_authenticated') and user.is_authenticated:
                bw_qs = BodyWeight.objects.filter(user=user, datetime__date=target_date).order_by('-datetime')
                if bw_qs.exists():
                    try:
                        bw_val = bw_qs.first().weight_lbs
                        if bw_val is not None and float(bw_val) > 0:
                            todays_bodyweight = float(bw_val)
                    except Exception:
                        todays_bodyweight = None
                # Fallback to profile preference/bodyweight_lbs
                if todays_bodyweight is None:
                    try:
                        fb = getattr(user, 'bodyweight_lbs', None)
                        if fb is not None and float(fb) > 0:
                            todays_bodyweight = float(fb)
                    except Exception:
                        todays_bodyweight = None
        except Exception:
            todays_bodyweight = None

        context['todays_bodyweight_lbs'] = todays_bodyweight

        # --- Stat Card Configuration Logic ---
        
        # 1. Define all possible stat cards and their properties
        ALL_STAT_CARDS = {
            'cardio_burned': {'title': 'CARDIO', 'metric_key': 'todays_total_calories', 'unit': 'KCAL BURNED', 'color': 'text-cyan-300', 'id': 'calories-value', 'suffix': '', 'detail_type': 'cardio'},
            'lifting_volume': {'title': 'LIFTING', 'metric_key': 'todays_lifting_volume_k', 'unit': 'Total Volume (lbs)', 'color': 'text-red-400', 'id': 'volume-value', 'suffix': 'k', 'detail_type': 'lifting'},
            'steps': {'title': 'STEPS', 'metric_key': 'todays_steps', 'unit': 'STEPS TAKEN', 'color': 'text-cyan-300', 'id': 'steps-value', 'suffix': '', 'detail_type': 'steps'},
            'calories_consumed': {'title': 'CALORIES', 'metric_key': 'todays_consumed_calories', 'unit': 'KCAL CONSUMED', 'color': 'text-red-400', 'id': 'consumed-value', 'suffix': '', 'detail_type': 'calories'},
            'water_intake': {'title': 'WATER', 'metric_key': 'todays_water_ounces', 'unit': 'OZ INTAKE', 'color': 'text-blue-400', 'id': 'water-value', 'suffix': '', 'detail_type': 'water'},
            'bodyweight': {'title': 'BODYWEIGHT', 'metric_key': 'todays_bodyweight_lbs', 'unit': 'CURRENT WEIGHT', 'color': 'text-purple-400', 'id': 'bodyweight-value', 'suffix': ' lbs', 'detail_type': 'bodyweight'},
        }

        # 2. Define default configuration (matching current template order)
        DEFAULT_CONFIG = [
            {'key': 'cardio_burned', 'visible': True, 'order': 1},
            {'key': 'lifting_volume', 'visible': True, 'order': 2},
            {'key': 'steps', 'visible': True, 'order': 3},
            {'key': 'calories_consumed', 'visible': True, 'order': 4},
            {'key': 'water_intake', 'visible': True, 'order': 5},
            {'key': 'bodyweight', 'visible': True, 'order': 6},
        ]

        # 3. Get user configuration, falling back to default
        user_config = kwargs.get('stat_card_config')
        if not user_config or not isinstance(user_config, list):
            user_config = DEFAULT_CONFIG
        
        # 4. Build the final list of cards
        final_cards = []
        for item in user_config:
            key = item.get('key')
            if item.get('visible', True) and key in ALL_STAT_CARDS:
                card_data = ALL_STAT_CARDS[key].copy()
                
                # Inject metric value
                metric_key = card_data['metric_key']
                value = context.get(metric_key)
                
                # Special handling for bodyweight formatting
                if key == 'bodyweight':
                    if value is not None and float(value) > 0:
                        #card_data['value'] = f"{float(value):.1f}"
                        card_data['value'] = float(value)
                        card_data['suffix'] = ' lbs'
                    else:
                        card_data['value'] = 'N/A'
                        card_data['suffix'] = ''
                elif key == 'water_intake':
                    #card_data['value'] = f"{float(value):.1f}"
                    card_data['value'] = float(value)
                else:
                    # Use intcomma formatting for large numbers in the template
                    #card_data['value'] = value
                    card_data['value'] = float(value)
    
                card_data['key'] = key
                card_data['order'] = item.get('order', 99)
                final_cards.append(card_data)
    
        # 5. Sort by order (if user config was provided, it should already be sorted, but good practice)
        final_cards.sort(key=lambda x: x['order'])

        context['stat_cards'] = final_cards
        context['ALL_STAT_CARDS'] = ALL_STAT_CARDS # Useful for configuration UI

        return context
