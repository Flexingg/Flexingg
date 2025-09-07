from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView, View, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse
from django.db.models import Avg, F, DecimalField
from django.utils import timezone
from django.contrib import messages
from base.ui import ui_base
from decimal import Decimal
from datetime import date, datetime, timedelta, timezone as dt_timezone
import logging
import tempfile
import os
import asyncio
import random
from asgiref.sync import sync_to_async

# Garmin Connect Imports - Using Garth directly
import garth
from garth.sso import login, exchange
from garth.exc import GarthException, GarthHTTPError

# Models and Forms
from .models import ( # Explicit imports
    WeightRecord, WeightGoal, WeightUnit,
    GarminDailySteps, GarminActivity, SweatScoreWeights
)
from .forms import WeightRecordForm, WeightGoalForm

# Import Garmin_Auth from base app
from base.models import Garmin_Auth, User, Friendship, UserColorPreference
from base.forms import ColorPickerForm
from setup_wizard.services import SetupService

logger = logging.getLogger(__name__)

# Step equivalents dictionary
step_equivalents = {
    "miles walked": 2000,  # Average steps per mile
    "kilometers walked": 1250,  # Average steps per kilometer
    "flights of stairs climbed": 20,  # Average steps per flight
    "trips around the world": 22500000,  # Earth's circumference in steps
    "marathon runs": 105000,  # Average steps in a marathon
    "Empire State Buildings climbed": 1500,  # Steps per building height
    "Everest summits": 10000,  # Steps equivalent to Everest height
    "laps around a football field": 100,  # Average steps per lap
    "mountains hiked": 50000,  # Average steps per mountain
    "rivers crossed": 10000,  # Steps to cross a river
    "oceans sailed": 1000000,  # Steps equivalent to ocean voyage
    "planets orbited": 1000000000,  # Steps equivalent to Earth's orbit
    "light years traveled": 1000000000000,  # Steps at light speed
    "lengths of a blue whale": 40,  # Length of a blue whale in steps
    "distances to the moon": 480500000,  # Distance to moon in steps
    "circumferences of Jupiter": 3500000000,  # Jupiter's circumference in steps
    "widths of the Milky Way": 900000000000000,  # Milky Way width in steps
    "distances across the Sahara": 50000000,  # Sahara Desert width in steps
    "lengths of an anaconda": 150,  # Length of an anaconda in steps
    "heights of the Eiffel Tower": 1000,  # Eiffel Tower height in steps
    "widths of the Grand Canyon": 20000,  # Grand Canyon width in steps
    "distances to Mars": 50000000000,  # Distance to Mars in steps
    "lengths of the Great Wall of China": 10000000,  # Great Wall length in steps
    "depths of the Mariana Trench": 10000,  # Mariana Trench depth in steps
    "spans of the Golden Gate Bridge": 2000,  # Golden Gate Bridge span in steps
    "heights of Burj Khalifa": 1000,  # Burj Khalifa height in steps
    "circumferences of a basketball": 10,  # Basketball circumference in steps
    "lengths of a football field": 100,  # Football field length in steps
    "distances to the International Space Station": 100000000,  # ISS distance in steps
    "widths of the Atlantic Ocean": 5000000000,  # Atlantic Ocean width in steps
    "heights of Mount Everest": 10000,  # Everest height in steps
    "lengths of the Nile River": 50000000,  # Nile River length in steps
    "spans of the Sydney Opera House": 1000,  # Sydney Opera House span in steps
    "depths of the Dead Sea": 500,  # Dead Sea depth in steps
    "widths of the Panama Canal": 10000,  # Panama Canal width in steps
    "heights of the Statue of Liberty": 200,  # Statue of Liberty height in steps
    "lengths of a Boeing 747": 100,  # Boeing 747 length in steps
    "distances to the Sun": 15000000000000,  # Distance to Sun in steps
    "circumferences of the Sun": 4000000000,  # Sun's circumference in steps
    "widths of the Solar System": 120000000000000,  # Solar System width in steps
    "lengths of a human hair": 0.1,  # Human hair length in steps
    "distances to Alpha Centauri": 40000000000000000,  # Distance to Alpha Centauri in steps
    "heights of the CN Tower": 500,  # CN Tower height in steps
    "lengths of the Amazon River": 60000000,  # Amazon River length in steps
    "widths of Australia": 400000000,  # Australia width in steps
    "depths of Lake Baikal": 10000,  # Lake Baikal depth in steps
    "spans of the Brooklyn Bridge": 500,  # Brooklyn Bridge span in steps
    "lengths of a T-Rex": 150,  # T-Rex length in steps
    "heights of the Leaning Tower of Pisa": 60,  # Leaning Tower height in steps
    "widths of the English Channel": 3000000,  # English Channel width in steps
    "distances to the North Pole": 200000000,  # North Pole distance in steps
    "lengths of the Yangtze River": 60000000,  # Yangtze River length in steps
    "depths of the Grand Canyon": 2000,  # Grand Canyon depth in steps
    "spans of the Tacoma Narrows Bridge": 1000,  # Tacoma Narrows span in steps
    "heights of the Washington Monument": 170,  # Washington Monument height in steps
    "lengths of a school bus": 150,  # School bus length in steps
    "distances to the South Pole": 250000000,  # South Pole distance in steps
    "circumferences of Earth": 22500000,  # Earth's circumference in steps
    "widths of the Pacific Ocean": 15000000000,  # Pacific Ocean width in steps
    "heights of the Space Needle": 180,  # Space Needle height in steps
    "lengths of the Mississippi River": 40000000,  # Mississippi River length in steps
    "depths of the Challenger Deep": 10000,  # Challenger Deep depth in steps
    "spans of the Verrazzano Bridge": 1500,  # Verrazzano Bridge span in steps
    "heights of the Petronas Towers": 450,  # Petronas Towers height in steps
    "lengths of a freight train": 2000,  # Freight train length in steps
    "distances to the edge of space": 10000000,  # Edge of space distance in steps
    "lengths of a sperm whale": 31,  # Length of a sperm whale in steps
    "distances to Pluto": 6000000000000,  # Distance to Pluto in steps
    "circumferences of the Moon": 13650000,  # Moon's circumference in steps
    "widths of the observable universe": 880000000000000000000000,  # Observable universe width in steps
    "lengths of a giant squid": 16,  # Length of a giant squid in steps
    "heights of Uluru": 348,  # Uluru height in steps
    "widths of the Strait of Gibraltar": 14000,  # Strait of Gibraltar width in steps
    "lengths of the Panama Canal": 82000,  # Panama Canal length in steps
    "depths of the Puerto Rico Trench": 8600,  # Puerto Rico Trench depth in steps
    "spans of the Akashi Kaikyo Bridge": 2000,  # Akashi Kaikyo Bridge span in steps
    "heights of the One World Trade Center": 540,  # One World Trade Center height in steps
    "lengths of the Trans-Siberian Railway": 9288000,  # Trans-Siberian Railway length in steps
    "widths of the Bay of Bengal": 1600000000,  # Bay of Bengal width in steps
    "depths of Crater Lake": 594,  # Crater Lake depth in steps
    "spans of the Millau Viaduct": 2460,  # Millau Viaduct span in steps
    "heights of Angel Falls": 979,  # Angel Falls height in steps
    "lengths of the Yellow River": 5464000,  # Yellow River length in steps
    "widths of Lake Superior": 160000000,  # Lake Superior width in steps
    "depths of the Caspian Sea": 1025,  # Caspian Sea depth in steps
    "spans of the Øresund Bridge": 7845,  # Øresund Bridge span in steps
    "heights of the Taipei 101": 508,  # Taipei 101 height in steps
    "lengths of the Danube River": 2860000,  # Danube River length in steps
    "widths of the Arabian Sea": 3860000000,  # Arabian Sea width in steps
    "depths of Lake Tanganyika": 1470,  # Lake Tanganyika depth in steps
    "spans of the Storebælt Bridge": 6604,  # Storebælt Bridge span in steps
    "heights of the Willis Tower": 442,  # Willis Tower height in steps
    "lengths of the Congo River": 4700000,  # Congo River length in steps
    "widths of Hudson Bay": 1230000000,  # Hudson Bay width in steps
    "depths of the Java Trench": 7450,  # Java Trench depth in steps
    "spans of the Confederation Bridge": 12900,  # Confederation Bridge span in steps
}

def relate_steps(steps):
    """
    Relates a given step count to random items from the step_equivalents dictionary,
    ensuring the quantity is less than 100 and not rounded to 0.00.

    Args:
        steps: The total number of steps taken (integer).

    Returns:
        A string sentence relating the steps to random items.
    """
    if steps < 0:
        return "How? "
    else:
        # Filter items so the resulting quantity is less than 100
        suitable_items = {
            name: equiv for name, equiv in step_equivalents.items()
            if equiv > 0 and steps / equiv < 100
        }

        if not suitable_items:
             # If no suitable items are found, pick the item with the largest equivalent value
            item_name, item_equiv = max(step_equivalents.items(), key=lambda item: item[1])
            quantity = steps / item_equiv
            return f"You've taken {steps} steps, which is equivalent to about {quantity:.2f} {item_name}."
        else:
            # Select items where the quantity is not rounded to 0.00
            displayable_items = {
                 name: equiv for name, equiv in suitable_items.items()
                 if f"{steps / equiv:.2f}" != "0.00"
            }

            if not displayable_items:
                 # If no displayable items are found, pick the item with the smallest equivalent value
                 item_name, item_equiv = min(suitable_items.items(), key=lambda item: item[1])
                 quantity = steps / item_equiv
                 return f"You've taken {steps} steps, which is equivalent to about {quantity:.2f} {item_name}."
            else:
                item_name, item_equiv = random.choice(list(displayable_items.items()))
                quantity = steps / item_equiv
                return f"You've taken {steps} steps, which is equivalent to about {quantity:.2f} {item_name}."


# Energy equivalents dictionary (purely energy-based)
calorie_equivalents = {
    "energy to boil a cup of water": 10000,
    "energy in a AA battery": 2000,
    "energy to run a 100W lightbulb for 1 hour": 86000,
    "energy to run a 60W lightbulb for 1 hour": 216000,
    "energy to run a laptop for 1 hour": 50000,
    "energy to run a refrigerator for 1 hour": 100000,
    "energy to run an air conditioner for 1 hour": 1000000,
    "energy to run a washing machine cycle": 500000,
    "energy to run a dishwasher cycle": 1000000,
    "energy to run a microwave for 1 minute": 10000,
    "energy to run a toaster for 1 minute": 5000,
    "energy to run a coffee maker": 100000,
    "energy to run a hair dryer for 1 minute": 100000,
    "energy to run a vacuum cleaner for 1 hour": 1000000,
    "energy to run a ceiling fan for 1 hour": 50000,
    "energy to run a space heater for 1 hour": 1500000,
    "energy to run a dehumidifier for 1 hour": 300000,
    "energy to run a water heater for 1 hour": 4000000,
    "energy to run a clothes dryer for 1 hour": 3000000,
    "energy to run a electric stove for 1 hour": 2000000,
    "energy to run a television for 1 hour": 50000,
    "energy to run a gaming console for 1 hour": 150000,
    "energy to run a smartphone charger for 1 hour": 5000,
    "energy to run a tablet charger for 1 hour": 10000,
    "energy to run a desktop computer for 1 hour": 200000,
    "energy to run a server for 1 hour": 500000,
    "energy to run a data center rack for 1 hour": 10000000,
    "energy to run a traffic light for 1 hour": 100000,
    "energy to run a street light for 1 hour": 200000,
    "energy to run a billboard for 1 hour": 500000,
    "energy to run a neon sign for 1 hour": 1000000,
    "energy to run a movie theater projector for 1 hour": 2000000,
    "energy to run a concert stage lighting for 1 hour": 5000000,
    "energy to run a radio station transmitter for 1 hour": 10000000,
    "energy to run a cell phone tower for 1 hour": 5000000,
    "energy to run a satellite for 1 hour": 10000000,
    "energy to run the International Space Station for 1 hour": 50000000,
    "energy to launch a SpaceX Falcon 9 rocket": 1000000000000,
    "energy to power a small town for 1 day": 100000000000,
    "energy to power a city for 1 day": 10000000000000,
    "energy to power a country for 1 day": 1000000000000000,
    "energy in a gallon of gasoline": 31000000,
    "energy in a gallon of diesel": 36000000,
    "energy in a gallon of jet fuel": 42000000,
    "energy in a gallon of propane": 25000000,
    "energy in a gallon of heating oil": 38000000,
    "energy in a ton of coal": 8000000000,
    "energy in a barrel of oil": 6000000000,
    "energy in a cubic foot of natural gas": 1000000,
    "energy in a wind turbine (per hour)": 2000000,
    "energy in a solar panel (per hour)": 300000,
    "energy in a hydroelectric dam (per hour)": 100000000,
    "energy in a nuclear power plant (per hour)": 1000000000,
    "energy in a geothermal plant (per hour)": 50000000,
    "energy in a tidal power generator (per hour)": 10000000,
    "energy in a wave energy converter (per hour)": 5000000,
    "energy released by a ton of TNT": 4184000000,
    "energy in a lightning strike": 5000000000,
    "energy in a volcanic eruption": 100000000000000,
    "energy in an earthquake": 1000000000000000,
    "energy in a hurricane (per second)": 52000000000000,
    "energy in a tornado": 1000000000000,
    "energy in a tsunami": 10000000000000000,
    "energy in a solar flare": 1000000000000000000,
    "energy in a supernova explosion": 1000000000000000000000000000,
    "energy to melt 1 kg of ice": 334000,
    "energy to vaporize 1 kg of water": 2260000,
    "energy to heat 1 kg of water by 1°C": 4186,
    "energy to compress air in a scuba tank": 2000000,
    "energy to accelerate a car to 60 mph": 1000000,
    "energy to lift 1 ton 1 meter": 9800,
    "energy to break chemical bonds in water": 500000000,
    "energy to split an atom": 1000000000000,
    "energy to fuse hydrogen atoms": 1000000000000000,
    "energy to create a black hole": 1000000000000000000000000000000,
    "energy in the Big Bang": 1000000000000000000000000000000000000000000000000,
    "energy to run a smartphone for 1 hour": 5000,
    "energy to charge a smartphone": 10000,
    "energy to run an LED light bulb for 1 hour": 10000,
    "energy to run a laptop for 30 minutes": 25000,
    "energy to run a refrigerator for 30 minutes": 50000,
    "energy to run an air conditioner for 30 minutes": 500000,
    "energy to run a washing machine for 30 minutes": 250000,
    "energy to run a dishwasher for 30 minutes": 500000,
    "energy to run a microwave for 30 seconds": 5000,
    "energy to run a toaster for 30 seconds": 2500,
    "energy to run a coffee maker for 5 minutes": 50000,
    "energy to run a hair dryer for 30 seconds": 50000,
    "energy to run a vacuum cleaner for 30 minutes": 500000,
    "energy to run a ceiling fan for 30 minutes": 25000,
    "energy to run a space heater for 30 minutes": 750000,
    "energy to run a water heater for 30 minutes": 2000000,
    "energy to run a clothes dryer for 30 minutes": 1500000,
    "energy to run an electric stove for 30 minutes": 1000000,
    "energy to run a television for 30 minutes": 25000,
    "energy to run a gaming console for 30 minutes": 75000,
    "energy to run a desktop computer for 30 minutes": 100000,
    "energy to run a server for 30 minutes": 250000,
    "energy to run a data center rack for 30 minutes": 5000000,
    "energy to run a traffic light for 30 minutes": 50000,
    "energy to run a street light for 30 minutes": 100000,
    "energy to run a billboard for 30 minutes": 250000,
    "energy to run a neon sign for 30 minutes": 500000,
    "energy to run a movie theater projector for 30 minutes": 1000000,
    "energy to run a concert stage lighting for 30 minutes": 2500000,
    "energy to run a radio station transmitter for 30 minutes": 5000000,
    "energy to run a cell phone tower for 30 minutes": 2500000,
    "energy to run a satellite for 30 minutes": 5000000,
    "energy to run the International Space Station for 30 minutes": 25000000,
    "energy to run a smartphone for 5 minutes": 500,
    "energy to run a smartphone for 10 minutes": 1000,
    "energy to charge a smartphone for 10 minutes": 800,
    "energy to run an LED light bulb for 5 minutes": 800,
    "energy to run a laptop for 5 minutes": 4000,
    "energy to run a refrigerator for 5 minutes": 8000,
    "energy to run an air conditioner for 5 minutes": 80000,
    "energy to run a washing machine for 5 minutes": 40000,
    "energy to run a dishwasher for 5 minutes": 80000,
    "energy to run a microwave for 5 seconds": 400,
    "energy to run a toaster for 5 seconds": 200,
    "energy to run a coffee maker for 1 minute": 10000,
    "energy to run a hair dryer for 5 seconds": 4000,
    "energy to run a vacuum cleaner for 5 minutes": 80000,
    "energy to run a ceiling fan for 5 minutes": 4000,
    "energy to run a space heater for 5 minutes": 120000,
    "energy to run a water heater for 5 minutes": 320000,
    "energy to run a clothes dryer for 5 minutes": 240000,
    "energy to run an electric stove for 5 minutes": 160000,
    "energy to run a television for 5 minutes": 4000,
    "energy to run a gaming console for 5 minutes": 12000,
    "energy to run a desktop computer for 5 minutes": 16000,
    "energy to run a server for 5 minutes": 40000,
    "energy to run a data center rack for 5 minutes": 800000,
    "energy to run a traffic light for 5 minutes": 8000,
    "energy to run a street light for 5 minutes": 16000,
    "energy to run a billboard for 5 minutes": 40000,
    "energy to run a neon sign for 5 minutes": 80000,
    "energy to run a movie theater projector for 5 minutes": 160000,
    "energy to run a concert stage lighting for 5 minutes": 400000,
    "energy to run a radio station transmitter for 5 minutes": 800000,
    "energy to run a cell phone tower for 5 minutes": 400000,
    "energy to run a satellite for 5 minutes": 800000
}

def relate_calories(calories):
    """
    Relates a given calorie amount to random items from the calorie_equivalents dictionary,
    ensuring the quantity is less than 100 and not rounded to 0.00.

    Args:
        calories: The total number of calories burned (integer).

    Returns:
        A string sentence relating the calories to random items.
    """
    if calories < 0:
        return "How? "
    else:
        # Filter items so the resulting quantity is less than 100
        suitable_items = {
            name: cal for name, cal in calorie_equivalents.items()
            if cal > 0 and calories / cal < 100
        }

        if not suitable_items:
              # If no suitable items are found, pick the item with the largest calorie value
            item_name, item_calories = max(calorie_equivalents.items(), key=lambda item: item[1])
            quantity = calories / item_calories
            return f"You've burned {calories} calories, which is {quantity:.2f}x the {item_name}."
        else:
            # Select items where the quantity is not rounded to 0.00
            displayable_items = {
                 name: cal for name, cal in suitable_items.items()
                 if f"{calories / cal:.2f}" != "0.00"
            }

            if not displayable_items:
                  # If no displayable items are found, pick the item with the smallest calorie value
                      item_name, item_calories = min(suitable_items.items(), key=lambda item: item[1])
                      quantity = calories / item_calories
                      return f"You've burned {calories} calories, which is {quantity:.2f}x the {item_name}."
            else:
                item_name, item_calories = random.choice(list(displayable_items.items()))
                quantity = calories / item_calories
                return f"You've burned {calories} calories, which is {quantity:.2f}x the {item_name}."


class FitnessDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'fitness/dashboard.html'

    def get_context_data(self, **kwargs):
        context = ui_base(self.request)
        context.update(super().get_context_data(**kwargs))

        # Add Garmin authentication context
        try:
            garmin_auth = Garmin_Auth.objects.get(user=self.request.user)
            context['garmin_linked'] = True
            context['garmin_last_sync'] = garmin_auth.last_sync

            # Initialize Garth client using stored OAuth tokens
            try:
                logger.info(f"Authenticating with Garth for user {self.request.user.id}")

                # Create OAuth token objects from stored data
                oauth1 = garth.auth_tokens.OAuth1Token(**garmin_auth._1())
                oauth2 = garth.auth_tokens.OAuth2Token(**garmin_auth._2())

                # Configure Garth client
                garth.client.configure(oauth1_token=oauth1, oauth2_token=oauth2)
                logger.info("Garth client configured successfully")

                # Test the connection by making a simple API call
                # We'll use the connectapi method directly
                try:
                    # Try a simpler endpoint that should work
                    test_response = garth.client.connectapi('/userprofile-service/socialProfile')
                    logger.info("Garth authentication test successful")
                except Exception as test_err:
                    logger.warning(f"Garth test API call failed: {test_err}")
                    # Try another endpoint
                    try:
                        test_response = garth.client.connectapi('/usersummary-service/usersummary')
                        logger.info("Garth authentication test successful (fallback endpoint)")
                    except Exception as fallback_err:
                        logger.warning(f"Garth fallback test API call also failed: {fallback_err}")
                        # Continue anyway - the authentication might still work for other endpoints

                # Get today's steps
                today = timezone.now().date()
                today_steps = GarminDailySteps.objects.filter(user=self.request.user, date=today).first()
                context['today_steps'] = today_steps.steps if today_steps else None

                # Get activity count
                context['activity_count'] = GarminActivity.objects.filter(user=self.request.user).count()

                # Get today's activities
                today_activities = GarminActivity.objects.filter(
                    user=self.request.user,
                    start_time_utc__date=today
                ).order_by('-start_time_utc')
                context['today_activities'] = today_activities

                context['garmin_auth_error'] = False

            except (GarthException, GarthHTTPError) as e:
                logger.warning(f"Garmin authentication error for user {self.request.user.username}: {str(e)}")
                context['garmin_auth_error'] = True
                context['today_steps'] = None
                context['activity_count'] = 0

            except Exception as e:
                logger.error(f"Error accessing Garmin data for user {self.request.user.username}: {str(e)}")
                context['garmin_auth_error'] = True
                context['today_steps'] = None
                context['activity_count'] = 0
                context['today_activities'] = []

        except Garmin_Auth.DoesNotExist as e:
            logger.info(f"No Garmin auth record found for user {self.request.user.id}: {str(e)}")
            # Check if there are any Garmin_Auth records at all for debugging
            total_auth_records = Garmin_Auth.objects.count()
            user_auth_records = Garmin_Auth.objects.filter(user=self.request.user).count()
            logger.info(f"Total Garmin_Auth records: {total_auth_records}, User records: {user_auth_records}")
            context['garmin_linked'] = False
            context['garmin_last_sync'] = None
            context['today_steps'] = None
            context['activity_count'] = 0
            context['today_activities'] = []
            context['garmin_auth_error'] = False
        except Exception as e:
            logger.error(f"Unexpected error checking Garmin auth for user {self.request.user.id}: {str(e)}")
            context['garmin_linked'] = False
            context['garmin_last_sync'] = None
            context['today_steps'] = None
            context['activity_count'] = 0
            context['today_activities'] = []
        
        
        
        # Check if background sync is needed
        sync_needed = False
        if context.get('garmin_linked'):
            try:
                garmin_auth = Garmin_Auth.objects.get(user=self.request.user)
                now = timezone.now()
                last_attempt = garmin_auth.last_sync_attempt

                # Debug logging
                logger.info(f"User {self.request.user.id} - Last sync attempt: {last_attempt}, Now: {now}")
                if last_attempt:
                    time_diff = (now - last_attempt).total_seconds()
                    logger.info(f"User {self.request.user.id} - Time since last attempt: {time_diff} seconds")

                # Sync if no attempt in last 10 minutes (600 seconds)
                if not last_attempt or (now - last_attempt).total_seconds() >= 600:
                    sync_needed = True
                    context['garmin_sync_needed'] = True
                    logger.info(f"User {self.request.user.id} - Background sync needed: True")
                else:
                    context['garmin_sync_needed'] = False
                    context['garmin_next_sync'] = (last_attempt + timedelta(minutes=10)).isoformat()
                    logger.info(f"User {self.request.user.id} - Background sync needed: False, next attempt: {context['garmin_next_sync']}")
            except Garmin_Auth.DoesNotExist:
                context['garmin_sync_needed'] = False
                logger.info(f"User {self.request.user.id} - No Garmin auth record found")

        # Add account component context variables
        # Get or create color preferences
        color_preferences, created = UserColorPreference.objects.get_or_create(user=self.request.user)

        # Get theme display name
        theme_choices = dict(ColorPickerForm.THEME_CHOICES)
        current_theme = theme_choices.get(color_preferences.theme_mode, 'Default')

        # Check if user is admin
        is_admin = self.request.user.is_superuser

        # Calculate setup progress
        setup_progress = SetupService.calculate_overall_progress(self.request.user)

        # Create API settings section
        api_fields = [{
            'name': 'gemini_key',
            'label': 'Gemini API Key',
            'value': self.request.user.custom_profile.gemini_key or '',
            'type': 'password',
            'help_text': 'Enter your Gemini API key for AI features',
        }]

        api_section = {
            'title': 'API Settings',
            'fields': api_fields
        }

        # Add server dates for JavaScript timezone handling
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)

        # Add to context
        context.update({
            'api_section': api_section,
            'color_preferences': color_preferences,
            'current_theme': current_theme,
            'is_admin': is_admin,
            'setup_progress': setup_progress,
            'today': today,
            'yesterday': yesterday
        })
        return context


class HealthView(LoginRequiredMixin, TemplateView):
    template_name = 'fitness/health.html'

    def get_context_data(self, **kwargs):
        context = ui_base(self.request)
        context.update(super().get_context_data(**kwargs))

        # Add weight-related context data
        try:
            context['weight_goal'] = WeightGoal.objects.get(user=self.request.user)
        except WeightGoal.DoesNotExist:
            context['weight_goal'] = None

        # Add available units for unit conversion
        context['weight_units'] = WeightUnit.objects.all()

        # Get weight records for the list
        context['weight_records'] = WeightRecord.objects.filter(user=self.request.user)[:10]  # Limit to recent records

        try:
            logger.info(f"Checking Garmin auth for user {self.request.user.id}")
            garmin_auth = Garmin_Auth.objects.get(user=self.request.user)
            logger.info(f"Found Garmin auth record for user {self.request.user.id}: {garmin_auth}")
            logger.info(f"Garmin auth details: oauth_token={garmin_auth.oauth_token[:10]}..., expires_at={garmin_auth.expires_at}")
            context['garmin_linked'] = True
            context['garmin_last_sync'] = garmin_auth.last_sync

            # Initialize Garth client using stored OAuth tokens
            try:
                logger.info(f"Authenticating with Garth for user {self.request.user.id}")

                # Create OAuth token objects from stored data
                oauth1 = garth.auth_tokens.OAuth1Token(**garmin_auth._1())
                oauth2 = garth.auth_tokens.OAuth2Token(**garmin_auth._2())

                # Configure Garth client
                garth.client.configure(oauth1_token=oauth1, oauth2_token=oauth2)
                logger.info("Garth client configured successfully")

                # Test the connection by making a simple API call
                # We'll use the connectapi method directly
                try:
                    # Try a simpler endpoint that should work
                    test_response = garth.client.connectapi('/userprofile-service/socialProfile')
                    logger.info("Garth authentication test successful")
                except Exception as test_err:
                    logger.warning(f"Garth test API call failed: {test_err}")
                    # Try another endpoint
                    try:
                        test_response = garth.client.connectapi('/usersummary-service/usersummary')
                        logger.info("Garth authentication test successful (fallback endpoint)")
                    except Exception as fallback_err:
                        logger.warning(f"Garth fallback test API call also failed: {fallback_err}")
                        # Continue anyway - the authentication might still work for other endpoints
                
                # Get today's steps
                today = timezone.now().date()
                today_steps = GarminDailySteps.objects.filter(user=self.request.user, date=today).first()
                context['today_steps'] = today_steps.steps if today_steps else None

                # Get activity count
                context['activity_count'] = GarminActivity.objects.filter(user=self.request.user).count()

                # Get today's activities
                today_activities = GarminActivity.objects.filter(
                    user=self.request.user,
                    start_time_utc__date=today
                ).order_by('-start_time_utc')
                context['today_activities'] = today_activities

                context['garmin_auth_error'] = False
                
            except (GarthException, GarthHTTPError) as e:
                logger.warning(f"Garmin authentication error for user {self.request.user.username}: {str(e)}")
                context['garmin_auth_error'] = True
                context['today_steps'] = None
                context['activity_count'] = 0

            except Exception as e:
                logger.error(f"Error accessing Garmin data for user {self.request.user.username}: {str(e)}")
                context['garmin_auth_error'] = True
                context['today_steps'] = None
                context['activity_count'] = 0
                context['today_activities'] = []

        except Garmin_Auth.DoesNotExist as e:
            logger.info(f"No Garmin auth record found for user {self.request.user.id}: {str(e)}")
            # Check if there are any Garmin_Auth records at all for debugging
            total_auth_records = Garmin_Auth.objects.count()
            user_auth_records = Garmin_Auth.objects.filter(user=self.request.user).count()
            logger.info(f"Total Garmin_Auth records: {total_auth_records}, User records: {user_auth_records}")
            context['garmin_linked'] = False
            context['garmin_last_sync'] = None
            context['today_steps'] = None
            context['activity_count'] = 0
            context['today_activities'] = []
            context['garmin_auth_error'] = False
        except Exception as e:
            logger.error(f"Unexpected error checking Garmin auth for user {self.request.user.id}: {str(e)}")
            context['garmin_linked'] = False
            context['garmin_last_sync'] = None
            context['today_steps'] = None
            context['activity_count'] = 0
            context['today_activities'] = []
            context['garmin_auth_error'] = False

        return context


# --- Background Sync for Health View ---

    def get_context_data(self, **kwargs):
        context = ui_base(self.request)
        context.update(super().get_context_data(**kwargs))

        # Add weight-related context data
        try:
            context['weight_goal'] = WeightGoal.objects.get(user=self.request.user)
        except WeightGoal.DoesNotExist:
            context['weight_goal'] = None

        # Add available units for unit conversion
        context['weight_units'] = WeightUnit.objects.all()

        # Get weight records for the list
        context['weight_records'] = WeightRecord.objects.filter(user=self.request.user)[:10]  # Limit to recent records

        # Check if background sync is needed for Garmin
        sync_needed = False
        try:
            logger.info(f"Checking Garmin auth for user {self.request.user.id}")
            garmin_auth = Garmin_Auth.objects.get(user=self.request.user)
            logger.info(f"Found Garmin auth record for user {self.request.user.id}: {garmin_auth}")
            logger.info(f"Garmin auth details: oauth_token={garmin_auth.oauth_token[:10]}..., expires_at={garmin_auth.expires_at}")
            context['garmin_linked'] = True
            context['garmin_last_sync'] = garmin_auth.last_sync

            # Check if background sync is needed
            now = timezone.now()
            last_attempt = garmin_auth.last_sync_attempt
            if not last_attempt or (now - last_attempt).total_seconds() >= 600:
                sync_needed = True
                context['garmin_sync_needed'] = True
            else:
                context['garmin_sync_needed'] = False
                context['garmin_next_sync'] = (last_attempt + timedelta(minutes=10)).isoformat()

            # Initialize Garth client using stored OAuth tokens
            try:
                logger.info(f"Authenticating with Garth for user {self.request.user.id}")

                # Create OAuth token objects from stored data
                oauth1 = garth.auth_tokens.OAuth1Token(**garmin_auth._1())
                oauth2 = garth.auth_tokens.OAuth2Token(**garmin_auth._2())

                # Configure Garth client
                garth.client.configure(oauth1_token=oauth1, oauth2_token=oauth2)
                logger.info("Garth client configured successfully")

                # Test the connection by making a simple API call
                # We'll use the connectapi method directly
                try:
                    # Try a simpler endpoint that should work
                    test_response = garth.client.connectapi('/userprofile-service/socialProfile')
                    logger.info("Garth authentication test successful")
                except Exception as test_err:
                    logger.warning(f"Garth test API call failed: {test_err}")
                    # Try another endpoint
                    try:
                        test_response = garth.client.connectapi('/usersummary-service/usersummary')
                        logger.info("Garth authentication test successful (fallback endpoint)")
                    except Exception as fallback_err:
                        logger.warning(f"Garth fallback test API call also failed: {fallback_err}")
                        # Continue anyway - the authentication might still work for other endpoints

                # Get today's steps
                today = timezone.now().date()
                today_steps = GarminDailySteps.objects.filter(user=self.request.user, date=today).first()
                context['today_steps'] = today_steps.steps if today_steps else None
                logger.info(f"Dashboard: Found {context['today_steps']} steps for today ({today}) for user {self.request.user.id}")

                # Get activity count
                activity_count = GarminActivity.objects.filter(user=self.request.user).count()
                context['activity_count'] = activity_count
                logger.info(f"Dashboard: Found {activity_count} total activities for user {self.request.user.id}")

                # Get today's activities
                today_activities = GarminActivity.objects.filter(
                    user=self.request.user,
                    start_time_utc__date=today
                ).order_by('-start_time_utc')
                context['today_activities'] = today_activities

                context['garmin_auth_error'] = False

            except (GarthException, GarthHTTPError) as e:
                logger.warning(f"Garmin authentication error for user {self.request.user.username}: {str(e)}")
                context['garmin_auth_error'] = True
                context['today_steps'] = None
                context['activity_count'] = 0

            except Exception as e:
                logger.error(f"Error accessing Garmin data for user {self.request.user.username}: {str(e)}")
                context['garmin_auth_error'] = True
                context['today_steps'] = None
                context['activity_count'] = 0
                context['today_activities'] = []

        except Garmin_Auth.DoesNotExist as e:
            logger.info(f"No Garmin auth record found for user {self.request.user.id}: {str(e)}")
            # Check if there are any Garmin_Auth records at all for debugging
            total_auth_records = Garmin_Auth.objects.count()
            user_auth_records = Garmin_Auth.objects.filter(user=self.request.user).count()
            logger.info(f"Total Garmin_Auth records: {total_auth_records}, User records: {user_auth_records}")
            context['garmin_linked'] = False
            context['garmin_last_sync'] = None
            context['today_steps'] = None
            context['activity_count'] = 0
            context['today_activities'] = []
            context['garmin_auth_error'] = False
        except Exception as e:
            logger.error(f"Unexpected error checking Garmin auth for user {self.request.user.id}: {str(e)}")
            context['garmin_linked'] = False
            context['garmin_last_sync'] = None
            context['today_steps'] = None
            context['activity_count'] = 0
            context['today_activities'] = []

        return context

# --- Weight Tracking Views (Existing code omitted for brevity) ---
# ... (WeightRecordListView, WeightRecordCreateView, etc.) ...
class WeightRecordListView(LoginRequiredMixin, ListView):
    model = WeightRecord
    template_name = 'fitness/weight_record_list.html'
    context_object_name = 'weight_records'
    paginate_by = 10

    def get_queryset(self):
        return WeightRecord.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = ui_base(self.request)
        context.update(super().get_context_data(**kwargs))
        try:
            context['weight_goal'] = WeightGoal.objects.get(user=self.request.user)
        except WeightGoal.DoesNotExist:
            context['weight_goal'] = None

        # Add available units for unit conversion
        context['weight_units'] = WeightUnit.objects.all()
        return context


class WeightRecordCreateView(LoginRequiredMixin, CreateView):
    model = WeightRecord
    form_class = WeightRecordForm
    template_name = 'fitness/weight_record_form.html'
    success_url = reverse_lazy('fitness:health')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = ui_base(self.request)
        context.update(super().get_context_data(**kwargs))
        context['kg_unit'] = WeightUnit.objects.get(symbol='kg')
        context['lb_unit'] = WeightUnit.objects.get(symbol='lbs')
        context['default_unit'] = context['lb_unit']
        return context


class WeightRecordUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = WeightRecord
    form_class = WeightRecordForm
    template_name = 'fitness/weight_record_form.html'
    success_url = reverse_lazy('fitness:health')

    def test_func(self):
        record = self.get_object()
        return record.user == self.request.user

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = ui_base(self.request)
        context.update(super().get_context_data(**kwargs))
        context['kg_unit'] = WeightUnit.objects.get(symbol='kg')
        context['lb_unit'] = WeightUnit.objects.get(symbol='lbs')
        context['default_unit'] = context['lb_unit']
        return context


class WeightRecordDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = WeightRecord
    template_name = 'fitness/weight_record_confirm_delete.html'
    success_url = reverse_lazy('fitness:health')

    def test_func(self):
        record = self.get_object()
        return record.user == self.request.user

    def get_context_data(self, **kwargs):
        context = ui_base(self.request)
        context.update(super().get_context_data(**kwargs))
        return context

    def delete(self, request, *args, **kwargs):
        """
        Handle the delete request. If it's an HTMX request, return an empty string to remove the element.
        Otherwise, use the default DeleteView behavior.
        """
        self.object = self.get_object()
        success_url = self.get_success_url()
        self.object.delete()
        
        if request.headers.get('HX-Request'):
            return HttpResponse('')  # Return empty string to remove the element
        return HttpResponseRedirect(success_url)


class WeightGoalCreateView(LoginRequiredMixin, CreateView):
    model = WeightGoal
    form_class = WeightGoalForm
    template_name = 'fitness/weight_goal_form.html'
    success_url = reverse_lazy('fitness:health')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = ui_base(self.request)
        context.update(super().get_context_data(**kwargs))
        context['kg_unit_id'] = WeightUnit.objects.get(symbol='kg').id
        context['lbs_unit_id'] = WeightUnit.objects.get(symbol='lbs').id
        context['default_unit_id'] = context['lbs_unit_id']  # Set lbs as default
        return context


class WeightGoalUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = WeightGoal
    form_class = WeightGoalForm
    template_name = 'fitness/weight_goal_form.html'
    success_url = reverse_lazy('fitness:health')

    def test_func(self):
        goal = self.get_object()
        return goal.user == self.request.user

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = ui_base(self.request)
        context.update(super().get_context_data(**kwargs))
        context['kg_unit_id'] = WeightUnit.objects.get(symbol='kg').id
        context['lbs_unit_id'] = WeightUnit.objects.get(symbol='lbs').id
        context['default_unit_id'] = context['lbs_unit_id']  # Set lbs as default
        return context


def get_chart_data(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    # Get the requested unit (default to lbs)
    try:
        display_unit_id = request.GET.get('unit')
        if display_unit_id:
            display_unit = WeightUnit.objects.get(id=display_unit_id)
        else:
            display_unit = WeightUnit.objects.get(symbol='lbs') # Default to lbs if no unit specified
    except WeightUnit.DoesNotExist:
        try:
            # Fallback if specified unit or lbs doesn't exist
            display_unit = WeightUnit.objects.first()
            if not display_unit:
                return JsonResponse({'error': 'No weight units configured in the system.'}, status=500)
            messages.warning(request, f"Requested or default weight unit not found. Using {display_unit.name}.")
        except Exception: # Catch potential errors during fallback
            return JsonResponse({'error': 'Error retrieving weight units.'}, status=500)


    # Get weight records and convert to requested unit
    records = WeightRecord.objects.filter(user=request.user).order_by('date')
    weight_data = [{
        'date': record.date.isoformat(), # Use ISO format for JS compatibility
        'weight': float(record.get_weight_in(display_unit))
    } for record in records]

    # Get weight goal if exists
    try:
        goal = WeightGoal.objects.get(user=request.user)
        goal_data = {
            'start_date': goal.start_date.isoformat(),
            'start_weight': float(goal.start_unit.convert_to(Decimal(str(goal.start_weight)), display_unit)),
            'target_date': goal.target_date.isoformat(),
            'target_weight': float(goal.target_unit.convert_to(Decimal(str(goal.target_weight)), display_unit))
        }
    except WeightGoal.DoesNotExist:
        goal_data = None

    # Calculate statistics in the requested unit
    stats = {
        'total_records': 0,
        'average_weight': None,
        'latest_weight': None,
        'first_weight': None,
        'unit_symbol': display_unit.symbol,
        'progress_percentage': None
    }

    if records.exists():
        # Use latest() and earliest() which are generally more efficient with default ordering
        latest_record = records.latest('date')
        first_record = records.earliest('date')
        latest_weight = float(latest_record.get_weight_in(display_unit))
        first_weight = float(first_record.get_weight_in(display_unit))

        # Calculate average weight in the requested unit
        # Convert all weights to kg first for aggregation
        avg_weight_kg_result = records.aggregate(avg_kg=Avg(F('weight') * F('unit__conversion_rate_to_kg'), output_field=DecimalField()))
        avg_weight_kg = avg_weight_kg_result['avg_kg']

        if avg_weight_kg is not None:
            # Ensure conversion_rate_to_kg is not zero
            if display_unit.conversion_rate_to_kg != 0:
                 avg_weight = float(Decimal(str(avg_weight_kg)) / display_unit.conversion_rate_to_kg)
            else:
                 avg_weight = None # Avoid division by zero
                 logger.error(f"WeightUnit {display_unit.symbol} has zero conversion rate.")
        else:
            avg_weight = None

        stats.update({
            'total_records': records.count(),
            'average_weight': avg_weight,
            'latest_weight': latest_weight,
            'first_weight': first_weight,
        })

        if goal_data:
            # Ensure weights are floats for calculation
            target_w = float(goal_data['target_weight'])
            start_w = float(goal_data['start_weight'])
            latest_w = float(latest_weight)

            total_change = target_w - start_w
            current_change = latest_w - start_w
            stats['progress_percentage'] = (current_change / total_change * 100) if total_change != 0 else (100 if current_change >= 0 else 0)


    return JsonResponse({
        'weight_data': weight_data,
        'goal_data': goal_data,
        'stats': stats
    })

# --- Garmin Connect Views ---

class LinkGarminStartView(LoginRequiredMixin, View):
    """
    Handles the initial step of linking a Garmin account: collecting the email.
    Stores the email in the session and redirects to the password entry page.
    """
    def post(self, request, *args, **kwargs):
        email = request.POST.get('garmin_email')
        if not email:
            messages.error(request, "Please enter your Garmin Connect email address.")
            return redirect(reverse_lazy('account')) # Adjust if your account URL name is different

        # Store email in session to pass to the next step (password entry)
        request.session['garmin_linking_email'] = email
        # messages.info(request, f"Please enter the password for {email} to complete linking.") # Message moved to password page
        # Redirect to the password entry view
        return redirect(reverse_lazy('fitness:link_garmin_password'))

class UnlinkGarminView(LoginRequiredMixin, View):
    """
    Handles unlinking a user's Garmin account by deleting their credentials.
    """
    def post(self, request, *args, **kwargs):
        try:
            garmin_auth = Garmin_Auth.objects.get(user=request.user)
            # Optionally: Add logic here to delete synced Garmin data if desired
            # GarminDailySteps.objects.filter(user=request.user).delete()
            # GarminActivity.objects.filter(user=request.user).delete()
            garmin_auth.delete()
            messages.success(request, "Your Garmin Connect account has been successfully unlinked.")
        except Garmin_Auth.DoesNotExist:
            messages.warning(request, "No Garmin Connect account was linked.")
        except Exception as e:
            logger.error(f"Error unlinking Garmin for user {request.user.id}: {e}", exc_info=True)
            messages.error(request, f"An error occurred while unlinking. Please try again.")

        return redirect(reverse_lazy('account')) # Adjust if your account URL name is different

class LinkGarminPasswordView(LoginRequiredMixin, TemplateView):
     template_name = 'fitness/garmin_password_form.html'

     def get_context_data(self, **kwargs):
         context = super().get_context_data(**kwargs)
         context['garmin_email'] = self.request.session.get('garmin_linking_email')
         # No redirect here, dispatch handles missing email check before rendering
         return context

     def dispatch(self, request, *args, **kwargs):
         # Check for email in session before rendering the page
         if not request.session.get('garmin_linking_email'):
             messages.error(request, "Garmin linking process incomplete or session expired. Please start again from your account page.")
             return redirect(reverse_lazy('account'))
         return super().dispatch(request, *args, **kwargs)

     def post(self, request, *args, **kwargs):
         logger.info(f"Garmin password POST received for user {request.user.id}")
         email = request.session.get('garmin_linking_email')
         password = request.POST.get('garmin_password')

         if not email: # Double check email, though dispatch should handle it
             logger.warning(f"No email in session for user {request.user.id}")
             messages.error(request, "Session expired. Please start the linking process again.")
             return redirect(reverse_lazy('account'))
         if not password:
             logger.warning(f"No password provided for user {request.user.id}")
             messages.error(request, "Password cannot be empty. Please try again.")
             # Return to the same page to show the error
             return render(request, self.template_name, self.get_context_data())

         logger.info(f"Starting Garmin login process for user {request.user.id} with email {email}")

         try:
             logger.info(f"Attempting Garmin login for user {request.user.id} with email {email}")

             # Clear any existing Garmin auth for this user first
             existing_auth = Garmin_Auth.objects.filter(user=request.user)
             if existing_auth.exists():
                 logger.info(f"Clearing {existing_auth.count()} existing Garmin auth for user {request.user.id}")
                 existing_auth.delete()

             # Use Garth SSO login directly (similar to your working Colab code)
             logger.info("Attempting Garth SSO login...")
             garth.login(email, password)
             logger.info("Garth login successful!")

             # Debug: Check what tokens we got
             logger.info(f"Garth client oauth1_token: {garth.client.oauth1_token}")
             logger.info(f"Garth client oauth2_token: {garth.client.oauth2_token}")

             # Get the OAuth tokens from Garth
             oauth1_token = garth.client.oauth1_token
             oauth2_token = garth.client.oauth2_token

             if not oauth1_token or not oauth2_token:
                 logger.error("Failed to obtain OAuth tokens from Garth")
                 messages.error(request, "Failed to obtain authentication tokens. Please try again.")
                 context = self.get_context_data()
                 return render(request, self.template_name, context)

             # Debug: Log OAuth1Token attributes
             logger.info(f"OAuth1Token attributes: {dir(oauth1_token)}")
             logger.info(f"OAuth1Token type: {type(oauth1_token)}")

             # Extract token data using correct attribute names
             oauth1_data = {}
             oauth2_data = {}

             # Use the correct OAuth1 attribute names
             if hasattr(oauth1_token, 'oauth_token'):
                 oauth1_data['oauth_token'] = oauth1_token.oauth_token
             else:
                 logger.error(f"OAuth1Token missing oauth_token attribute: {oauth1_token}")
                 messages.error(request, "Failed to extract OAuth1 token data.")
                 context = self.get_context_data()
                 return render(request, self.template_name, context)

             if hasattr(oauth1_token, 'oauth_token_secret'):
                 oauth1_data['oauth_token_secret'] = oauth1_token.oauth_token_secret
             else:
                 logger.error(f"OAuth1Token missing oauth_token_secret attribute: {oauth1_token}")
                 messages.error(request, "Failed to extract OAuth1 token secret.")
                 context = self.get_context_data()
                 return render(request, self.template_name, context)

             # Add other OAuth1 attributes
             for attr in ['mfa_token', 'mfa_expiration_timestamp', 'domain']:
                 if hasattr(oauth1_token, attr):
                     oauth1_data[attr] = getattr(oauth1_token, attr)

             # Extract OAuth2 data
             for attr in ['scope', 'jti', 'token_type', 'access_token', 'refresh_token',
                         'expires_in', 'expires_at', 'refresh_token_expires_in', 'refresh_token_expires_at']:
                 if hasattr(oauth2_token, attr):
                     oauth2_data[attr] = getattr(oauth2_token, attr)

             # Combine the data
             garmin_auth_data = {
                   'user': request.user,
                   'garmin_email': email,
                   **oauth1_data,
                   **oauth2_data
               }

             garmin_auth_record = Garmin_Auth.objects.create(**garmin_auth_data)
             logger.info(f"Successfully stored Garmin auth for user {request.user.id}: {garmin_auth_record}")
             logger.info(f"Created Garmin_Auth with oauth_token: {garmin_auth_record.oauth_token[:10]}...")

             # Verify the record was created by querying it back
             verify_record = Garmin_Auth.objects.filter(user=request.user).first()
             if verify_record:
                 logger.info(f"Verification successful: Garmin_Auth record exists for user {request.user.id}")
             else:
                 logger.error(f"Verification failed: Garmin_Auth record NOT found after creation for user {request.user.id}")

             # Clear sensitive info from session
             if 'garmin_linking_email' in request.session:
                 del request.session['garmin_linking_email']

             logger.info(f"Garmin account linked successfully for user {request.user.id}")
             messages.success(request, f"Garmin account ({email}) linked successfully!")
             logger.info(f"Redirecting to account page for user {request.user.id}")
             return redirect(reverse_lazy('account'))

         except GarthException as e:
             logger.warning(f"Garmin authentication failed for user {request.user.id} with email {email}: {e}")
             error_str = str(e).lower()
             if "invalid" in error_str or "credentials" in error_str:
                 messages.error(request, "Garmin login failed: Incorrect email or password.")
             elif "mfa" in error_str or "multi-factor" in error_str or "2fa" in error_str:
                 messages.error(request, "Multi-Factor Authentication (MFA) may be required. Please check your Garmin account settings.")
             else:
                 messages.error(request, f"Garmin login failed: {str(e)[:100]}...")

         except Exception as e:
             logger.error(f"Unexpected error during Garmin login for user {request.user.id}: {e}", exc_info=True)
             messages.error(request, f"Garmin login failed: {str(e)[:100]}... Please try again or contact support if the issue persists.")

         # If any exception occurred, render the form again with errors
         context = self.get_context_data()
         return render(request, self.template_name, context)
 
 
class SyncGarminDataView(LoginRequiredMixin, View):
    """
    Handles triggering the Garmin data synchronization process.
    Fetches data using the stored Garth tokens and saves it to the database.
    """
    async def post(self, request, *args, **kwargs):
        try:
            garmin_auth = await sync_to_async(Garmin_Auth.objects.get)(user=request.user)
            print(f"Found Garmin auth for user {request.user.id}: {garmin_auth}")
            print(f"Garmin auth details: oauth_token={garmin_auth.oauth_token[:10]}..., expires_at={garmin_auth.expires_at}")
            print(f"Current time: {time.time()}")
        except Garmin_Auth.DoesNotExist:
            messages.error(request, "Garmin account not linked. Please link your account first.")
            return redirect(reverse_lazy('fitness:dashboard'))

        sync_start_time = timezone.now()
        steps_synced = 0
        activities_synced = 0

        try:

            # Check if tokens are expired and try to refresh if needed
            if garmin_auth.expired():
                print("Tokens expired, attempting refresh...")
                print(f"Token expires_at: {garmin_auth.expires_at}, current time: {time.time()}")
                try:
                    # Create OAuth1Token object from stored data
                    oauth1_data = garmin_auth._1()
                    oauth1_token = garth.auth_tokens.OAuth1Token(**oauth1_data)

                    # Create OAuth2Token object from stored data
                    oauth2_data = garmin_auth._2()
                    oauth2_token = garth.auth_tokens.OAuth2Token(**oauth2_data)

                    # Configure garth client first, then refresh
                    garth.client.configure(oauth1_token=oauth1_token, oauth2_token=oauth2_token)

                    # Try to refresh the tokens using the configured client
                    exchange(oauth1_token, client=garth.client)

                    # Update the stored tokens with refreshed data
                    garmin_auth.oauth_token = oauth1_token.oauth_token
                    garmin_auth.oauth_token_secret = oauth1_token.oauth_token_secret
                    garmin_auth.mfa_token = getattr(oauth1_token, 'mfa_token', None)
                    garmin_auth.mfa_expiration_timestamp = getattr(oauth1_token, 'mfa_expiration_timestamp', None)
                    garmin_auth.domain = getattr(oauth1_token, 'domain', None)

                    garmin_auth.scope = oauth2_token.scope
                    garmin_auth.jti = oauth2_token.jti
                    garmin_auth.token_type = oauth2_token.token_type
                    garmin_auth.access_token = oauth2_token.access_token
                    garmin_auth.refresh_token = oauth2_token.refresh_token
                    garmin_auth.expires_in = oauth2_token.expires_in
                    garmin_auth.expires_at = oauth2_token.expires_at
                    garmin_auth.refresh_token_expires_in = getattr(oauth2_token, 'refresh_token_expires_in', None)
                    garmin_auth.refresh_token_expires_at = getattr(oauth2_token, 'refresh_token_expires_at', None)

                    garmin_auth.save()  # Save updated tokens
                    logger.info("Token refresh successful")
                except Exception as refresh_err:
                    logger.error(f"Token refresh failed for user {request.user.id}: {refresh_err}")
                    messages.error(request, "Garmin authentication token expired. Please re-link your account.")
                    return redirect(reverse_lazy('fitness:dashboard'))

            # Configure Garth client with stored tokens
            oauth1 = garth.auth_tokens.OAuth1Token(**garmin_auth._1())
            oauth2 = garth.auth_tokens.OAuth2Token(**garmin_auth._2())
            garth.client.configure(oauth1_token=oauth1, oauth2_token=oauth2)
            logger.info("Garth client configured for sync")

            # --- Determine Sync Range ---
            end_date = timezone.now().date()
            date_range = request.POST.get('date_range', 'current_month')

            if date_range == 'current_month':
                start_date_steps = end_date.replace(day=1)
                activity_limit = 500
            elif date_range == 'last_3_months':
                start_date_steps = (end_date.replace(day=1) - timedelta(days=60)).replace(day=1)
                activity_limit = 500
            elif date_range == 'this_year':
                start_date_steps = end_date.replace(month=1, day=1)
                activity_limit = 500
            elif date_range == 'all_time':
                start_date_steps = end_date - timedelta(days=730)  # 2 years (more reasonable)
                activity_limit = 1000
            else:
                # Default to current month
                start_date_steps = end_date.replace(day=1)
                activity_limit = 500

            logger.info(f"Syncing range: {start_date_steps} to {end_date} for user {request.user.id} (range: {date_range})")

            # --- Sync Steps ---
            logger.info(f"Syncing steps from {start_date_steps} to {end_date} for user {request.user.id}")
            days_to_sync = (end_date - start_date_steps).days + 1
            logger.info(f"Total days to sync: {days_to_sync}")

            # Limit to prevent timeouts - max 365 days
            if days_to_sync > 365:
                logger.warning(f"Too many days to sync ({days_to_sync}), limiting to 365 days")
                start_date_steps = end_date - timedelta(days=364)

            current_date = start_date_steps
            days_processed = 0
            while current_date <= end_date:
                try:
                    # Skip future dates
                    if current_date > timezone.now().date():
                        logger.info(f"Skipping future date {current_date} for user {request.user.id}")
                        current_date += timedelta(days=1)
                        continue

                    # Fetch steps for the current day using Garth connectapi
                    # Try the working endpoint pattern from base functions
                    url = f"/usersummary-service/stats/steps/daily/{current_date.isoformat()}/{current_date.isoformat()}"
                    try:
                        daily_steps_data = garth.client.connectapi(url)
                    except Exception as api_err:
                        logger.warning(f"Steps API failed for {current_date}: {api_err}")
                        # Try alternative endpoint if the first one fails
                        try:
                            alt_url = f"/usersummary-service/usersummary/daily/{current_date.isoformat()}"
                            daily_steps_data = garth.client.connectapi(alt_url)
                            logger.info(f"Used alternative steps endpoint for {current_date}")
                        except Exception as alt_err:
                            logger.warning(f"Alternative steps API also failed for {current_date}: {alt_err}")
                            continue

                    if daily_steps_data and len(daily_steps_data) > 0:
                        steps = daily_steps_data[0].get('totalSteps', 0)
                        if steps is not None:  # Ensure steps value exists
                            obj, created = await sync_to_async(GarminDailySteps.objects.update_or_create)(
                                user=request.user,
                                date=current_date,
                                defaults={'steps': steps}
                            )
                            if created:
                                steps_synced += 1

                except Exception as step_err:
                    # Log error for specific day but continue sync
                    logger.error(f"Error syncing steps for {current_date} for user {request.user.id}: {step_err}", exc_info=True)
                current_date += timedelta(days=1)
                days_processed += 1

                # Log progress every 50 days
                if days_processed % 50 == 0:
                    logger.info(f"Processed {days_processed} days for user {request.user.id}")
            logger.info(f"Finished syncing steps for user {request.user.id}. Synced: {steps_synced} new records.")

            # --- Sync Activities ---
            logger.info(f"Syncing last {activity_limit} activities for user {request.user.id}")
            url = f"/activitylist-service/activities/search/activities?start=0&limit={activity_limit}"
            activities = garth.client.connectapi(url)

            # Process activities
            for activity in activities:
                try:
                    activity_id = activity.get('activityId')
                    if not activity_id:
                        logger.warning(f"Skipping activity with missing ID for user {request.user.id}: {activity}")
                        continue

                    start_ts_gmt = activity.get('startTimeGMT')
                    start_time_utc = None
                    if start_ts_gmt:
                        try:
                            if isinstance(start_ts_gmt, str):
                                # Check if it's a datetime string like "2025-09-01 16:43:04"
                                if ' ' in start_ts_gmt and '-' in start_ts_gmt:
                                    # Parse datetime string
                                    start_time_utc = datetime.strptime(start_ts_gmt, '%Y-%m-%d %H:%M:%S')
                                    # Assume it's already in UTC (Garmin typically provides UTC times)
                                    start_time_utc = start_time_utc.replace(tzinfo=dt_timezone.utc)
                                else:
                                    # Try to convert Unix timestamp string to float
                                    start_ts_gmt = float(start_ts_gmt)
                                    start_time_utc = datetime.fromtimestamp(start_ts_gmt / 1000, tz=dt_timezone.utc)
                            elif isinstance(start_ts_gmt, (int, float)):
                                # Unix timestamp in milliseconds
                                start_time_utc = datetime.fromtimestamp(start_ts_gmt / 1000, tz=dt_timezone.utc)
                            else:
                                logger.warning(f"Unexpected start time type for activity {activity_id}: {type(start_ts_gmt)} - {start_ts_gmt}")
                                continue
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Invalid start time format for activity {activity_id}: {start_ts_gmt} - {e}")
                            continue
                    else:
                        logger.warning(f"Missing start time for activity {activity_id} for user {request.user.id}")
                        continue

                    defaults = {
                        'name': activity.get('activityName', 'Unnamed Activity'),
                        'activity_type': activity.get('activityType', {}).get('typeKey', 'unknown'),
                        'start_time_utc': start_time_utc,
                        'duration_seconds': activity.get('duration'),
                        'distance_meters': activity.get('distance'),
                        'calories': activity.get('calories'),
                        'average_hr': activity.get('averageHR'),
                        'max_hr': activity.get('maxHR'),
                        'raw_data': activity
                    }
                    defaults = {k: v for k, v in defaults.items() if v is not None}

                    obj, created = await sync_to_async(GarminActivity.objects.update_or_create)(
                        user=request.user,
                        activity_id=activity_id,
                        defaults=defaults
                    )
                    if created:
                        activities_synced += 1

                except Exception as act_err:
                    logger.error(f"Error processing activity {activity.get('activityId', 'N/A')} for user {request.user.id}: {act_err}", exc_info=True)

            logger.info(f"Finished syncing activities for user {request.user.id}. Synced: {steps_synced} new records.")

            # --- Update Last Sync Timestamp ---
            logger.info(f"Updating last_sync timestamp to {sync_start_time} for user {request.user.id}")
            garmin_auth.last_sync = sync_start_time
            await sync_to_async(garmin_auth.save)(update_fields=['last_sync'])
            logger.info(f"Successfully updated last_sync timestamp for user {request.user.id}")

            messages.success(request, f"Garmin data sync complete. Synced {steps_synced} daily step records and {activities_synced} activities.")

        except GarthException as e:
            logger.error(f"Garmin API error during sync for user {request.user.id}: {e}", exc_info=True)
            messages.error(request, f"Error connecting to Garmin during sync: {e}. Please try again later or re-link your account if the issue persists.")
        except Exception as e:
            logger.error(f"Unexpected error during Garmin sync for user {request.user.id}: {e}", exc_info=True)
            messages.error(request, f"An unexpected error occurred during sync: {e}")

        return redirect(reverse_lazy('fitness:dashboard'))


# --- Background Sync Functions ---

def perform_background_garmin_sync(user):
    """
    Synchronous function to perform Garmin data sync.
    Reuses logic from SyncGarminDataView.
    """
    
    try:
        garmin_auth = Garmin_Auth.objects.get(user=user)
        
    except Garmin_Auth.DoesNotExist:
        
        return {'success': False, 'error': 'No Garmin auth record'}

    sync_start_time = timezone.now()
    steps_synced = 0
    activities_synced = 0

    try:
        logger.info(f"Starting background Garmin sync for user {request.user.id}")

        # Check if tokens are expired and try to refresh if needed
        if garmin_auth.expired():
            logger.info(f"Tokens expired for user {request.user.id}, attempting refresh...")
            try:
                # Create OAuth1Token object from stored data
                oauth1_data = garmin_auth._1()
                oauth1_token = garth.auth_tokens.OAuth1Token(**oauth1_data)

                # Create OAuth2Token object from stored data
                oauth2_data = garmin_auth._2()
                oauth2_token = garth.auth_tokens.OAuth2Token(**oauth2_data)

                # Configure garth client first, then refresh
                garth.client.configure(oauth1_token=oauth1_token, oauth2_token=oauth2_token)

                # Try to refresh the tokens using the configured client
                exchange(oauth1_token, client=garth.client)

                # Update the stored tokens with refreshed data
                garmin_auth.oauth_token = oauth1_token.oauth_token
                garmin_auth.oauth_token_secret = oauth1_token.oauth_token_secret
                garmin_auth.mfa_token = getattr(oauth1_token, 'mfa_token', None)
                garmin_auth.mfa_expiration_timestamp = getattr(oauth1_token, 'mfa_expiration_timestamp', None)
                garmin_auth.domain = getattr(oauth1_token, 'domain', None)

                garmin_auth.scope = oauth2_token.scope
                garmin_auth.jti = oauth2_token.jti
                garmin_auth.token_type = oauth2_token.token_type
                garmin_auth.access_token = oauth2_token.access_token
                garmin_auth.refresh_token = oauth2_token.refresh_token
                garmin_auth.expires_in = oauth2_token.expires_in
                garmin_auth.expires_at = oauth2_token.expires_at
                garmin_auth.refresh_token_expires_in = getattr(oauth2_token, 'refresh_token_expires_in', None)
                garmin_auth.refresh_token_expires_at = getattr(oauth2_token, 'refresh_token_expires_at', None)

                garmin_auth.save()  # Save updated tokens
                logger.info("Token refresh successful")
            except Exception as refresh_err:
                logger.error(f"Token refresh failed for user {user.id}: {refresh_err}")
                # Try to proceed with existing tokens - they might still work
                try:
                    # Configure client with original tokens
                    oauth1_data = garmin_auth._1()
                    oauth2_data = garmin_auth._2()
                    oauth1 = garth.auth_tokens.OAuth1Token(**oauth1_data)
                    oauth2 = garth.auth_tokens.OAuth2Token(**oauth2_data)
                    garth.client.configure(oauth1_token=oauth1, oauth2_token=oauth2)
                except Exception as config_err:
                    logger.error(f"Failed to configure client with existing tokens for user {user.id}: {config_err}")
                    return {'success': False, 'error': 'Token refresh failed and cannot configure client'}

        # Configure Garth client with stored tokens
        oauth1_data = garmin_auth._1()
        oauth2_data = garmin_auth._2()
        oauth1 = garth.auth_tokens.OAuth1Token(**oauth1_data)
        oauth2 = garth.auth_tokens.OAuth2Token(**oauth2_data)
        garth.client.configure(oauth1_token=oauth1, oauth2_token=oauth2)
        

        # --- Determine Sync Range ---
        end_date = timezone.now().date()
        # For background sync, use default range (could be made configurable later)
        date_range = 'current_month'  # Default for background sync

        if date_range == 'current_month':
            start_date_steps = end_date.replace(day=1)
            activity_limit = 500
        elif date_range == 'last_3_months':
            start_date_steps = (end_date.replace(day=1) - timedelta(days=60)).replace(day=1)
            activity_limit = 500
        elif date_range == 'this_year':
            start_date_steps = end_date.replace(month=1, day=1)
            activity_limit = 500
        elif date_range == 'all_time':
            start_date_steps = end_date - timedelta(days=730)  # 2 years (more reasonable)
            activity_limit = 1000
        else:
            # Default to current month
            start_date_steps = end_date.replace(day=1)
            activity_limit = 500

        logger.info(f"Background sync range: {start_date_steps} to {end_date} for user {user.id}")

        
        
        
        

        # --- Sync Steps ---

        # Ensure we don't go back more than 90 days (Garmin API limitation)
        max_lookback_days = 90
        if (end_date - start_date_steps).days > max_lookback_days:
            start_date_steps = end_date - timedelta(days=max_lookback_days)

        days_to_sync = (end_date - start_date_steps).days + 1
        logger.info(f"Background sync: Total days to sync: {days_to_sync}")

        current_date = start_date_steps
        days_processed = 0
        while current_date <= end_date:
            try:
                # Skip future dates
                if current_date > timezone.now().date():
                    
                    current_date += timedelta(days=1)
                    continue

                # Fetch steps for the current day using Garth connectapi
                url = f"/usersummary-service/stats/steps/daily/{current_date.isoformat()}/{current_date.isoformat()}"
                
                try:
                    daily_steps_data = garth.client.connectapi(url)
                    
                except Exception as api_err:
                    
                    # Try alternative endpoint if the first one fails
                    try:
                        alt_url = f"/usersummary-service/usersummary/daily/{current_date.isoformat()}"
                        
                        daily_steps_data = garth.client.connectapi(alt_url)
                        
                    except Exception as alt_err:
                        
                        continue

                if daily_steps_data and len(daily_steps_data) > 0:
                    steps = daily_steps_data[0].get('totalSteps', 0)
                    
                    if steps is not None:  # Ensure steps value exists
                        obj, created = GarminDailySteps.objects.update_or_create(
                            user=user,
                            date=current_date,
                            defaults={'steps': steps}
                        )
                        if created:
                            steps_synced += 1
                    else:
                        logger.warning(f"No steps value found in API response for {current_date}")

            except Exception as step_err:
                # Log error for specific day but continue sync
                logger.error(f"Error syncing steps for {current_date} for user {user.id}: {step_err}", exc_info=True)
            current_date += timedelta(days=1)
            days_processed += 1

            # Log progress every 20 days for background sync
            if days_processed % 20 == 0:
                logger.info(f"Background sync processed {days_processed} days for user {user.id}")
        

        # --- Sync Activities ---
        
        activities_url = f"/activitylist-service/activities/search/activities?start=0&limit={activity_limit}"
        activities = garth.client.connectapi(activities_url)

        if activities:
            pass
            

        # Process activities
        for i, activity in enumerate(activities):
            try:
                activity_id = activity.get('activityId')
                logger.info(f"Processing activity {i+1}/{len(activities)}: ID={activity_id}, Name={activity.get('activityName', 'Unknown')}")
                if not activity_id:
                    logger.warning(f"Skipping activity with missing ID for user {user.id}: {activity}")
                    continue

                start_ts_gmt = activity.get('startTimeGMT')
                start_time_utc = None
                if start_ts_gmt:
                    try:
                        if isinstance(start_ts_gmt, str):
                            # Check if it's a datetime string like "2025-09-01 16:43:04"
                            if ' ' in start_ts_gmt and '-' in start_ts_gmt:
                                # Parse datetime string
                                start_time_utc = datetime.strptime(start_ts_gmt, '%Y-%m-%d %H:%M:%S')
                                # Assume it's already in UTC (Garmin typically provides UTC times)
                                start_time_utc = start_time_utc.replace(tzinfo=dt_timezone.utc)
                            else:
                                # Try to convert Unix timestamp string to float
                                start_ts_gmt = float(start_ts_gmt)
                                start_time_utc = datetime.fromtimestamp(start_ts_gmt / 1000, tz=dt_timezone.utc)
                        elif isinstance(start_ts_gmt, (int, float)):
                            # Unix timestamp in milliseconds
                            start_time_utc = datetime.fromtimestamp(start_ts_gmt / 1000, tz=dt_timezone.utc)
                        else:
                            logger.warning(f"Unexpected start time type for activity {activity_id}: {type(start_ts_gmt)} - {start_ts_gmt}")
                            continue
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Invalid start time format for activity {activity_id}: {start_ts_gmt} - {e}")
                        continue
                else:
                    logger.warning(f"Missing start time for activity {activity_id} for user {user.id}")
                    continue

                defaults = {
                    'name': activity.get('activityName', 'Unnamed Activity'),
                    'activity_type': activity.get('activityType', {}).get('typeKey', 'unknown'),
                    'start_time_utc': start_time_utc,
                    'duration_seconds': activity.get('duration'),
                    'distance_meters': activity.get('distance'),
                    'calories': activity.get('calories'),
                    'average_hr': activity.get('averageHR'),
                    'max_hr': activity.get('maxHR'),
                    'raw_data': activity
                }
                defaults = {k: v for k, v in defaults.items() if v is not None}

                obj, created = GarminActivity.objects.update_or_create(
                    user=user,
                    activity_id=activity_id,
                    defaults=defaults
                )
                if created:
                    activities_synced += 1
                    
                else:
                    logger.info(f"Activity {activity_id} already exists for user {user.id}, skipping creation.")
            except Exception as act_err:
                logger.error(f"Error processing activity {activity.get('activityId', 'N/A')} for user {user.id}: {act_err}", exc_info=True)

        logger.info(f"Finished syncing activities for user {user.id}. Synced: {steps_synced} new records.")

        # --- Update Last Sync Timestamp ---
        garmin_auth.last_sync = sync_start_time
        garmin_auth.save(update_fields=['last_sync'])

        
        return {
            'success': True,
            'steps_synced': steps_synced,
            'activities_synced': activities_synced
        }

    except GarthException as e:
        logger.error(f"Garmin API error during background sync for user {user.id}: {e}", exc_info=True)
        return {'success': False, 'error': f'Garmin API error: {str(e)}'}
    except Exception as e:
        logger.error(f"Unexpected error during background Garmin sync for user {user.id}: {e}", exc_info=True)
        return {'success': False, 'error': f'Unexpected error: {str(e)}'}


class BackgroundGarminSyncView(LoginRequiredMixin, View):
    """
    API endpoint to trigger background Garmin sync.
    Returns JSON response indicating if sync was started or skipped.
    """

    def post(self, request, *args, **kwargs):
        try:
            garmin_auth = Garmin_Auth.objects.get(user=request.user)
        except Garmin_Auth.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Garmin account not linked'
            }, status=400)

        # Check if we should attempt sync (60-second threshold)
        now = timezone.now()
        last_attempt = garmin_auth.last_sync_attempt

        if last_attempt and (now - last_attempt).total_seconds() < 600:  # 10 minutes
            return JsonResponse({
                'success': False,
                'skipped': True,
                'reason': 'Sync attempted too recently',
                'next_attempt': (last_attempt + timedelta(minutes=10)).isoformat()
            })

        # Update last sync attempt timestamp immediately
        garmin_auth.last_sync_attempt = now
        garmin_auth.save(update_fields=['last_sync_attempt'])

        logger.info(f"Background Garmin sync triggered for user {request.user.id} at {now}")

        # Start background sync - try synchronous approach first
        
        try:
            # Run synchronously for now to test if the sync logic works
            result = perform_background_garmin_sync(request.user)
            
            return JsonResponse(result)
        except Exception as e:
            
            return JsonResponse({
                'success': False,
                'error': f'Sync failed: {str(e)}'
            }, status=500)


def weight_stats(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    # Get weight records for the user
    records = WeightRecord.objects.filter(user=request.user)
    
    # Initialize stats dictionary
    stats = {
        'total_records': records.count(),
        'average_weight': None,
        'latest_weight': None,
        'progress_percentage': None
    }

    if records.exists():
        # Calculate average weight
        avg_weight = records.aggregate(Avg('weight'))['weight__avg']
        if avg_weight is not None:
            stats['average_weight'] = float(avg_weight)

        # Get latest weight
        latest_record = records.order_by('-date').first()
        if latest_record:
            stats['latest_weight'] = float(latest_record.weight)

        # Calculate progress percentage if there's a goal
        try:
            goal = WeightGoal.objects.get(user=request.user)
            if stats['latest_weight'] is not None:
                total_change = float(goal.target_weight - goal.start_weight)
                current_change = float(stats['latest_weight'] - goal.start_weight)
                stats['progress_percentage'] = (current_change / total_change * 100) if total_change != 0 else 0
        except WeightGoal.DoesNotExist:
            pass

    return JsonResponse(stats)

class GarminActivityListView(LoginRequiredMixin, ListView):
    model = GarminActivity
    template_name = 'fitness/garmin_activity_list.html'
    context_object_name = 'activities'
    paginate_by = 10

    def get_queryset(self):
        return GarminActivity.objects.filter(user=self.request.user).order_by('-start_time_utc')

    def get_context_data(self, **kwargs):
        context = ui_base(self.request)
        context.update(super().get_context_data(**kwargs))
        return context

class GarminActivityDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = GarminActivity
    template_name = 'fitness/garmin_activity_detail.html'
    context_object_name = 'activity'
    pk_url_kwarg = 'pk'

    def test_func(self):
        activity = self.get_object()

        # Allow activity owner to view their own activities
        if activity.user == self.request.user:
            return True

        # Check if current user is friends with activity owner
        friendships_as_from = Friendship.objects.filter(
            from_user=self.request.user,
            to_user=activity.user,
            status='accepted'
        )

        friendships_as_to = Friendship.objects.filter(
            from_user=activity.user,
            to_user=self.request.user,
            status='accepted'
        )

        return friendships_as_from.exists() or friendships_as_to.exists()

    def get_context_data(self, **kwargs):
        context = ui_base(self.request)
        context.update(super().get_context_data(**kwargs))

        # Add information about whether this is the user's own activity
        activity = self.get_object()
        context['is_own_activity'] = activity.user == self.request.user
        context['activity_owner'] = activity.user

        return context

class WeightQuickAddView(LoginRequiredMixin, View):
    def post(self, request):
        weight = request.POST.get('weight')
        unit_id = request.POST.get('unit')
        
        if not weight:
            return JsonResponse({'error': 'Missing weight value'}, status=400)
            
        if not unit_id:
            # Default to lbs if no unit specified
            unit_id = WeightUnit.objects.get(symbol='lbs').id
            
        try:
            unit = WeightUnit.objects.get(id=unit_id)
            record = WeightRecord.objects.create(
                user=request.user,
                weight=float(weight),
                unit=unit,
                date=timezone.now().date()
            )
            
            # Return the new record as HTML to be inserted
            return render(request, 'fitness/components/weight_record_card.html', {
                'record': record,
                'weight_units': WeightUnit.objects.all()
            })
        except (ValueError, WeightUnit.DoesNotExist) as e:
            return JsonResponse({'error': str(e)}, status=400)

class WeightTrendDataView(LoginRequiredMixin, View):
    def get(self, request):
        # Get date range from query parameters
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        # Default to last 30 days if no range specified
        if not start_date or not end_date:
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=30)
        else:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # Get weight records in date range
        records = WeightRecord.objects.filter(
            user=request.user,
            date__range=[start_date, end_date]
        ).order_by('date')
        
        # Convert all weights to lbs for consistent charting
        data = {
            'labels': [record.date.strftime('%Y-%m-%d') for record in records],
            'weights': [float(record.get_weight_in(WeightUnit.objects.get(symbol='lbs'))) for record in records],
            'goal': None
        }
        
        # Add goal data if exists
        try:
            goal = WeightGoal.objects.get(user=request.user)
            if goal.start_date <= end_date and goal.target_date >= start_date:
                data['goal'] = {
                    'start_weight': float(goal.get_weight_in(WeightUnit.objects.get(symbol='lbs'))),
                    'target_weight': float(goal.target_weight),
                    'start_date': goal.start_date.strftime('%Y-%m-%d'),
                    'target_date': goal.target_date.strftime('%Y-%m-%d')
                }
        except WeightGoal.DoesNotExist:
            pass
        
        return JsonResponse(data)

def api_weight_detail(request, record_id):
    """Handle API operations for a specific weight record"""
    if request.method == 'DELETE':
        record = get_object_or_404(WeightRecord, id=record_id, user=request.user)
        record.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'error': 'Method not allowed'}, status=405)


class SocialActivityFeedView(LoginRequiredMixin, ListView):
    """
    Displays a social feed of Garmin activities from friends/following users.
    Shows activities in chronological order (most recent first) with filtering options.
    """
    model = GarminActivity
    template_name = 'fitness/social_activity_feed.html'
    context_object_name = 'activities'
    paginate_by = 20

    def get_queryset(self):
        # Get accepted friendships for the current user (both directions)
        friendships_as_from = Friendship.objects.filter(
            from_user=self.request.user, 
            status='accepted'
        ).values_list('to_user', flat=True)
        
        friendships_as_to = Friendship.objects.filter(
            to_user=self.request.user, 
            status='accepted'
        ).values_list('from_user', flat=True)
        
        # Combine friend user IDs
        friend_user_ids = list(friendships_as_from) + list(friendships_as_to)
        

        # Get selected friends from query parameters (if any)
        selected_friends = self.request.GET.getlist('friends')

        if selected_friends:
            # Filter to only selected friends
            friend_ids = [int(fid) for fid in selected_friends if fid.isdigit()]
            friend_user_ids = [fid for fid in friend_user_ids if fid in friend_ids]
            

        # Include the current user's activities as well
        following_user_ids = friend_user_ids + [self.request.user.id]

        # Get activities from friends AND current user, ordered by most recent first
        queryset = GarminActivity.objects.filter(
            user_id__in=following_user_ids
        ).select_related('user', 'user__custom_profile').order_by('-start_time_utc')

        # Apply activity type filter if specified
        selected_activity_types = self.request.GET.getlist('activity_types')
        if selected_activity_types:
            queryset = queryset.filter(activity_type__in=selected_activity_types)

        return queryset

    def get_context_data(self, **kwargs):
        context = ui_base(self.request)
        context.update(super().get_context_data(**kwargs))

        # Get accepted friendships for the current user
        friendships_as_from = Friendship.objects.filter(
            from_user=self.request.user,
            status='accepted'
        )

        friendships_as_to = Friendship.objects.filter(
            to_user=self.request.user,
            status='accepted'
        )

        # Get friend User objects
        friend_users = []
        for friendship in friendships_as_from:
            friend_users.append(friendship.to_user)
        for friendship in friendships_as_to:
            friend_users.append(friendship.from_user)

        # Get currently selected friends
        selected_friends = self.request.GET.getlist('friends')
        selected_friend_ids = [int(fid) for fid in selected_friends if fid.isdigit()]

        # Get selected activity types
        selected_activity_types = self.request.GET.getlist('activity_types')

        # Get all unique activity types from visible activities for the filter dropdown
        following_user_ids = [user.id for user in friend_users] + [self.request.user.id]
        base_queryset = GarminActivity.objects.filter(user_id__in=following_user_ids)
        available_activity_types = base_queryset.values_list('activity_type', flat=True).distinct().order_by('activity_type')
        available_activity_types = [at for at in available_activity_types if at]  # Remove None values

        # Get the queryset and paginate it
        queryset = self.get_queryset()

        # Handle pagination
        page = self.request.GET.get('page')
        paginator = self.paginator_class(queryset, self.paginate_by)
        page_obj = paginator.get_page(page)
        is_paginated = page_obj.has_other_pages()

        context.update({
            'following_users': friend_users,
            'selected_friend_ids': selected_friend_ids,
            'available_activity_types': available_activity_types,
            'selected_activity_types': selected_activity_types,
            'total_activities': queryset.count(),
            'filter_applied': bool(selected_friends) or bool(selected_activity_types),
            'is_paginated': is_paginated,
            'page_obj': page_obj,
        })

        return context

def get_calories_chart_data(request):
    """API endpoint for calories chart data with friends' data and podium rankings"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    # Get the requested range (default to current_month)
    range_param = request.GET.get('range', 'current_month')

    # Calculate date range based on the requested period
    today = timezone.now().date()
    if range_param == 'current_month':
        start_date = today.replace(day=1)
        end_date = today
    elif range_param == 'last_month':
        # Get last month
        first_of_this_month = today.replace(day=1)
        last_of_last_month = first_of_this_month - timedelta(days=1)
        start_date = last_of_last_month.replace(day=1)
        end_date = last_of_last_month
    elif range_param == 'last_3_months':
        # Last 3 months including current
        start_date = (today.replace(day=1) - timedelta(days=60)).replace(day=1)
        end_date = today
    elif range_param == 'last_year':
        # Last year
        start_date = today.replace(year=today.year - 1, month=1, day=1)
        end_date = today
    elif range_param == 'alltime':
        # All time
        start_date = date(2000, 1, 1)
        end_date = today
    else:  # Default to current month
        start_date = today.replace(day=1)
        end_date = today

    # Get user's calories data
    user_activities = GarminActivity.objects.filter(
        user=request.user,
        start_time_utc__date__range=[start_date, end_date],
        calories__isnull=False
    ).exclude(calories=0)

    # Aggregate user calories by date
    user_calories_by_date = {}
    for activity in user_activities:
        date_key = activity.start_time_utc.date().isoformat()
        user_calories_by_date[date_key] = user_calories_by_date.get(date_key, 0) + (activity.calories or 0)

    # Make user data cumulative
    cumulative_calories = 0
    user_data = []
    current_date = start_date
    while current_date <= end_date:
        date_key = current_date.isoformat()
        daily_calories = user_calories_by_date.get(date_key, 0)
        cumulative_calories += daily_calories
        user_data.append({'date': date_key, 'calories': cumulative_calories})
        current_date += timedelta(days=1)

    # Get friends' data
    friendships_as_from = Friendship.objects.filter(
        from_user=request.user,
        status='accepted'
    ).values_list('to_user', flat=True)

    friendships_as_to = Friendship.objects.filter(
        to_user=request.user,
        status='accepted'
    ).values_list('from_user', flat=True)

    friend_user_ids = list(friendships_as_from) + list(friendships_as_to)

    friends_data = []
    all_users_calories = []  # For podium ranking

    # Add user's total for ranking
    user_total_calories = sum(activity.calories or 0 for activity in user_activities)
    if user_total_calories > 0:
        all_users_calories.append({
            'user_id': request.user.id,
            'name': request.user.username,
            'calories': user_total_calories
        })

    # Get friends' data
    for friend_id in friend_user_ids:
        try:
            friend = User.objects.get(id=friend_id)
            friend_activities = GarminActivity.objects.filter(
                user=friend,
                start_time_utc__date__range=[start_date, end_date],
                calories__isnull=False
            ).exclude(calories=0)

            friend_calories_by_date = {}
            for activity in friend_activities:
                date_key = activity.start_time_utc.date().isoformat()
                friend_calories_by_date[date_key] = friend_calories_by_date.get(date_key, 0) + (activity.calories or 0)

            # Always include friends, even if they have no data (they'll show as flat line at 0)
            # Make friend data cumulative with all days in range
            cumulative_calories = 0
            friend_data = []
            current_date = start_date
            while current_date <= end_date:
                date_key = current_date.isoformat()
                daily_calories = friend_calories_by_date.get(date_key, 0)
                cumulative_calories += daily_calories
                friend_data.append({'date': date_key, 'calories': cumulative_calories})
                current_date += timedelta(days=1)

            friends_data.append({
                'name': friend.username,
                'data': friend_data
            })

            # Add to ranking (only if they have activities)
            friend_total = sum(activity.calories or 0 for activity in friend_activities)
            if friend_total > 0:
                all_users_calories.append({
                    'user_id': friend.id,
                    'name': friend.username,
                    'calories': friend_total
                })

        except User.DoesNotExist:
            continue

    # Calculate podium rankings
    all_users_calories.sort(key=lambda x: x['calories'], reverse=True)
    podium_data = []
    for i, user_info in enumerate(all_users_calories[:3]):
        podium_data.append({
            'name': user_info['name'],
            'calories': int(user_info['calories'])
        })

    # Calculate stats - get the final cumulative value for each friend
    friends_totals = []
    for friend_data in friends_data:
        if friend_data['data']:
            # Get the last (most recent) cumulative value
            final_value = friend_data['data'][-1]['calories']
            friends_totals.append(final_value)
    friends_average = sum(friends_totals) / len(friends_totals) if friends_totals else 0

    # Find user's rank
    user_rank = None
    for i, user_info in enumerate(all_users_calories):
        if user_info['user_id'] == request.user.id:
            user_rank = i + 1
            break

    stats = {
        'user_total': int(user_total_calories),
        'friends_average': int(friends_average) if friends_average else 0,
        'user_rank': user_rank,
        'sentence': relate_calories(int(user_total_calories)) if user_total_calories > 0 else "No calories burned yet!"
    }

    return JsonResponse({
        'user_data': user_data,
        'friends_data': friends_data,
        'podium_data': podium_data,
        'stats': stats,
        'date_range': {
            'start': start_date.isoformat(),
            'end': end_date.isoformat()
        }
    })

def get_steps_chart_data(request):
    """API endpoint for steps chart data with friends' data and podium rankings"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    # Get the requested range (default to current_month)
    range_param = request.GET.get('range', 'current_month')

    # Calculate date range based on the requested period
    today = timezone.now().date()
    if range_param == 'current_month':
        start_date = today.replace(day=1)
        end_date = today
    elif range_param == 'last_month':
        # Get last month
        first_of_this_month = today.replace(day=1)
        last_of_last_month = first_of_this_month - timedelta(days=1)
        start_date = last_of_last_month.replace(day=1)
        end_date = last_of_last_month
    elif range_param == 'last_3_months':
        # Last 3 months including current
        start_date = (today.replace(day=1) - timedelta(days=60)).replace(day=1)
        end_date = today
    elif range_param == 'last_year':
        # Last year
        start_date = today.replace(year=today.year - 1, month=1, day=1)
        end_date = today
    elif range_param == 'alltime':
        # All time
        start_date = date(2000, 1, 1)
        end_date = today
    else:  # Default to current month
        start_date = today.replace(day=1)
        end_date = today

    # Get user's steps data from GarminDailySteps
    user_steps_records = GarminDailySteps.objects.filter(
        user=request.user,
        date__range=[start_date, end_date]
    ).order_by('date')

    # Aggregate user steps by date
    user_steps_by_date = {}
    for record in user_steps_records:
        date_key = record.date.isoformat()
        user_steps_by_date[date_key] = record.steps

    # Make user data cumulative
    cumulative_steps = 0
    user_data = []
    current_date = start_date
    while current_date <= end_date:
        date_key = current_date.isoformat()
        daily_steps = user_steps_by_date.get(date_key, 0)
        cumulative_steps += daily_steps
        user_data.append({'date': date_key, 'steps': cumulative_steps})
        current_date += timedelta(days=1)

    # Get friends' data
    friendships_as_from = Friendship.objects.filter(
        from_user=request.user,
        status='accepted'
    ).values_list('to_user', flat=True)

    friendships_as_to = Friendship.objects.filter(
        to_user=request.user,
        status='accepted'
    ).values_list('from_user', flat=True)

    friend_user_ids = list(friendships_as_from) + list(friendships_as_to)

    friends_data = []
    all_users_steps = []  # For podium ranking

    # Add user's total for ranking
    user_total_steps = sum(record.steps for record in user_steps_records)
    if user_total_steps > 0:
        all_users_steps.append({
            'user_id': request.user.id,
            'name': request.user.username,
            'steps': user_total_steps
        })

    # Get friends' data
    for friend_id in friend_user_ids:
        try:
            friend = User.objects.get(id=friend_id)
            friend_steps_records = GarminDailySteps.objects.filter(
                user=friend,
                date__range=[start_date, end_date]
            )

            friend_steps_by_date = {}
            for record in friend_steps_records:
                date_key = record.date.isoformat()
                friend_steps_by_date[date_key] = record.steps

            # Always include friends, even if they have no data (they'll show as flat line at 0)
            # Make friend data cumulative with all days in range
            cumulative_steps = 0
            friend_data = []
            current_date = start_date
            while current_date <= end_date:
                date_key = current_date.isoformat()
                daily_steps = friend_steps_by_date.get(date_key, 0)
                cumulative_steps += daily_steps
                friend_data.append({'date': date_key, 'steps': cumulative_steps})
                current_date += timedelta(days=1)

            friends_data.append({
                'name': friend.username,
                'data': friend_data
            })

            # Add to ranking (only if they have steps)
            friend_total = sum(record.steps for record in friend_steps_records)
            if friend_total > 0:
                all_users_steps.append({
                    'user_id': friend.id,
                    'name': friend.username,
                    'steps': friend_total
                })

        except User.DoesNotExist:
            continue

    # Calculate podium rankings
    all_users_steps.sort(key=lambda x: x['steps'], reverse=True)
    podium_data = []
    for i, user_info in enumerate(all_users_steps[:3]):
        podium_data.append({
            'name': user_info['name'],
            'steps': int(user_info['steps'])
        })

    # Calculate stats - get the final cumulative value for each friend
    friends_totals = []
    for friend_data in friends_data:
        if friend_data['data']:
            # Get the last (most recent) cumulative value
            final_value = friend_data['data'][-1]['steps']
            friends_totals.append(final_value)
    friends_average = sum(friends_totals) / len(friends_totals) if friends_totals else 0

    # Find user's rank
    user_rank = None
    for i, user_info in enumerate(all_users_steps):
        if user_info['user_id'] == request.user.id:
            user_rank = i + 1
            break

    stats = {
        'user_total': int(user_total_steps),
        'friends_average': int(friends_average) if friends_average else 0,
        'user_rank': user_rank,
        'sentence': relate_steps(int(user_total_steps)) if user_total_steps > 0 else "No steps taken yet!"
    }

    return JsonResponse({
        'user_data': user_data,
        'friends_data': friends_data,
        'podium_data': podium_data,
        'stats': stats,
        'date_range': {
            'start': start_date.isoformat(),
            'end': end_date.isoformat()
        }
    })


def calculate_sweat_score(activity, weights_dict):
    """
    Calculate sweat score for a single activity based on HR zones and weights.
    Returns the calculated score or fallback value.
    """
    # Try to get HR zone data from raw_data
    if activity.raw_data and 'hrTimeInZone' in activity.raw_data:
        hr_zones = activity.raw_data['hrTimeInZone']

        # Extract time in each zone (convert from seconds to minutes)
        t1 = hr_zones.get('hrTimeInZone_1', 0) / 60  # Zone 1
        t2 = hr_zones.get('hrTimeInZone_2', 0) / 60  # Zone 2
        t3 = hr_zones.get('hrTimeInZone_3', 0) / 60  # Zone 3
        t4 = hr_zones.get('hrTimeInZone_4', 0) / 60  # Zone 4
        t5 = hr_zones.get('hrTimeInZone_5', 0) / 60  # Zone 5

        # Calculate T0 (time below zone 1)
        total_duration = (activity.duration_seconds or 0) / 60  # Convert to minutes
        t0 = max(0, total_duration - (t1 + t2 + t3 + t4 + t5))

        # Calculate score using weights
        score = (
            (t0 * float(weights_dict.get(0, 1))) +
            (t1 * float(weights_dict.get(1, 2))) +
            (t2 * float(weights_dict.get(2, 3))) +
            (t3 * float(weights_dict.get(3, 5))) +
            (t4 * float(weights_dict.get(4, 8))) +
            (t5 * float(weights_dict.get(5, 12)))
        )

        return score
    else:
        # Fallback: use calories / 2
        if activity.calories:
            return activity.calories / 2
        return 0


def get_sweat_score_chart_data(request):
    """API endpoint for sweat score chart data with friends' data and podium rankings"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    # Get the requested range (default to current_month)
    range_param = request.GET.get('range', 'current_month')

    # Calculate date range based on the requested period
    today = timezone.now().date()
    if range_param == 'current_month':
        start_date = today.replace(day=1)
        end_date = today
    elif range_param == 'last_month':
        # Get last month
        first_of_this_month = today.replace(day=1)
        last_of_last_month = first_of_this_month - timedelta(days=1)
        start_date = last_of_last_month.replace(day=1)
        end_date = last_of_last_month
    elif range_param == 'last_3_months':
        # Last 3 months including current
        start_date = (today.replace(day=1) - timedelta(days=60)).replace(day=1)
        end_date = today
    elif range_param == 'last_year':
        # Last year
        start_date = today.replace(year=today.year - 1, month=1, day=1)
        end_date = today
    elif range_param == 'alltime':
        # All time
        start_date = date(2000, 1, 1)
        end_date = today
    else:  # Default to current month
        start_date = today.replace(day=1)
        end_date = today

    # Get sweat score weights
    weights = SweatScoreWeights.objects.all()
    weights_dict = {weight.zone: weight.weight for weight in weights}

    # Get user's activities data
    user_activities = GarminActivity.objects.filter(
        user=request.user,
        start_time_utc__date__range=[start_date, end_date]
    ).exclude(duration_seconds__isnull=True).exclude(duration_seconds=0)

    # Aggregate user sweat scores by date
    user_scores_by_date = {}
    for activity in user_activities:
        date_key = activity.start_time_utc.date().isoformat()
        score = calculate_sweat_score(activity, weights_dict)
        user_scores_by_date[date_key] = user_scores_by_date.get(date_key, 0) + score

    # Make user data cumulative
    cumulative_score = 0
    user_data = []
    current_date = start_date
    while current_date <= end_date:
        date_key = current_date.isoformat()
        daily_score = user_scores_by_date.get(date_key, 0)
        cumulative_score += daily_score
        user_data.append({'date': date_key, 'score': cumulative_score})
        current_date += timedelta(days=1)

    # Get friends' data
    friendships_as_from = Friendship.objects.filter(
        from_user=request.user,
        status='accepted'
    ).values_list('to_user', flat=True)

    friendships_as_to = Friendship.objects.filter(
        to_user=request.user,
        status='accepted'
    ).values_list('from_user', flat=True)

    friend_user_ids = list(friendships_as_from) + list(friendships_as_to)

    friends_data = []
    all_users_scores = []  # For podium ranking

    # Add user's total for ranking
    user_total_score = sum(calculate_sweat_score(activity, weights_dict) for activity in user_activities)
    if user_total_score > 0:
        all_users_scores.append({
            'user_id': request.user.id,
            'name': request.user.username,
            'score': user_total_score
        })

    # Get friends' data
    for friend_id in friend_user_ids:
        try:
            friend = User.objects.get(id=friend_id)
            friend_activities = GarminActivity.objects.filter(
                user=friend,
                start_time_utc__date__range=[start_date, end_date]
            ).exclude(duration_seconds__isnull=True).exclude(duration_seconds=0)

            friend_scores_by_date = {}
            for activity in friend_activities:
                date_key = activity.start_time_utc.date().isoformat()
                score = calculate_sweat_score(activity, weights_dict)
                friend_scores_by_date[date_key] = friend_scores_by_date.get(date_key, 0) + score

            # Always include friends, even if they have no data (they'll show as flat line at 0)
            # Make friend data cumulative with all days in range
            cumulative_score = 0
            friend_data = []
            current_date = start_date
            while current_date <= end_date:
                date_key = current_date.isoformat()
                daily_score = friend_scores_by_date.get(date_key, 0)
                cumulative_score += daily_score
                friend_data.append({'date': date_key, 'score': cumulative_score})
                current_date += timedelta(days=1)

            friends_data.append({
                'name': friend.username,
                'data': friend_data
            })

            # Add to ranking (only if they have activities)
            friend_total = sum(calculate_sweat_score(activity, weights_dict) for activity in friend_activities)
            if friend_total > 0:
                all_users_scores.append({
                    'user_id': friend.id,
                    'name': friend.username,
                    'score': friend_total
                })

        except User.DoesNotExist:
            continue

    # Calculate podium rankings
    all_users_scores.sort(key=lambda x: x['score'], reverse=True)
    podium_data = []
    for i, user_info in enumerate(all_users_scores[:3]):
        podium_data.append({
            'name': user_info['name'],
            'score': int(user_info['score'])
        })

    # Calculate stats - get the final cumulative value for each friend
    friends_totals = []
    for friend_data in friends_data:
        if friend_data['data']:
            # Get the last (most recent) cumulative value
            final_value = friend_data['data'][-1]['score']
            friends_totals.append(final_value)
    friends_average = sum(friends_totals) / len(friends_totals) if friends_totals else 0

    # Find user's rank
    user_rank = None
    for i, user_info in enumerate(all_users_scores):
        if user_info['user_id'] == request.user.id:
            user_rank = i + 1
            break

    stats = {
        'user_total': int(user_total_score),
        'friends_average': int(friends_average) if friends_average else 0,
        'user_rank': user_rank
    }

    return JsonResponse({
        'user_data': user_data,
        'friends_data': friends_data,
        'podium_data': podium_data,
        'stats': stats,
        'date_range': {
            'start': start_date.isoformat(),
            'end': end_date.isoformat()
        }
    })
