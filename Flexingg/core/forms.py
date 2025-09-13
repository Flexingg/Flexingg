
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import get_user_model

User = get_user_model()


class LoginForm(AuthenticationForm):

    username = forms.CharField(
        label='Gamertag',
        widget=forms.TextInput(attrs={
            'class': 'pixel-input',
            'placeholder': 'Gamertag',
            'style': 'background-color: #1c1c1c !important; border: 2px solid #444 !important; box-shadow: inset -2px -2px 0px 0px #000, inset 2px 2px 0px 0px #555 !important; font-family: "Press Start 2P", cursive !important; color: #E0E0E0 !important; padding: 0.5rem !important; width: 100% !important; font-size: 12px !important; outline: none !important; -webkit-appearance: none !important; -moz-appearance: none !important; appearance: none !important;'
        })
    )

    password = forms.CharField(
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'pixel-input',
            'placeholder': 'Enter your password',
            'style': 'background-color: #1c1c1c !important; border: 2px solid #444 !important; box-shadow: inset -2px -2px 0px 0px #000, inset 2px 2px 0px 0px #555 !important; font-family: "Press Start 2P", cursive !important; color: #E0E0E0 !important; padding: 0.5rem !important; width: 100% !important; font-size: 12px !important; outline: none !important; -webkit-appearance: none !important; -moz-appearance: none !important; appearance: none !important;'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Gamertag'

class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'avatar', 'email', 'height_ft', 'height_in', 'weight', 'sex', 'sync_debounce_minutes']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'pixel-input',
                'placeholder': 'Update your username',
                'style': 'background-color: #1c1c1c !important; border: 2px solid #444 !important; box-shadow: inset -2px -2px 0px 0px #000, inset 2px 2px 0px 0px #555 !important; font-family: "Press Start 2P", cursive !important; color: #E0E0E0 !important; padding: 0.5rem !important; width: 100% !important; font-size: 12px !important; outline: none !important; -webkit-appearance: none !important; -moz-appearance: none !important; appearance: none !important;'
            }), 
            'email': forms.EmailInput(attrs={
                'class': 'pixel-input',
                'placeholder': 'Update your email',
                'style': 'background-color: #1c1c1c !important; border: 2px solid #444 !important; box-shadow: inset -2px -2px 0px 0px #000, inset 2px 2px 0px 0px #555 !important; font-family: "Press Start 2P", cursive !important; color: #E0E0E0 !important; padding: 0.5rem !important; width: 100% !important; font-size: 12px !important; outline: none !important; -webkit-appearance: none !important; -moz-appearance: none !important; appearance: none !important;'
            }),
            'height_ft': forms.NumberInput(attrs={
                'class': 'pixel-input',
                'placeholder': 'ft',
                'style': 'background-color: #1c1c1c !important; border: 2px solid #444 !important; box-shadow: inset -2px -2px 0px 0px #000, inset 2px 2px 0px 0px #555 !important; font-family: "Press Start 2P", cursive !important; color: #E0E0E0 !important; padding: 0.5rem !important; width: 100% !important; font-size: 12px !important; outline: none !important; -webkit-appearance: none !important; -moz-appearance: none !important; appearance: none !important; padding-right: 2rem !important;'
            }), 
            'height_in': forms.NumberInput(attrs={
                'class': 'pixel-input',
                'placeholder': 'in',
                'style': 'background-color: #1c1c1c !important; border: 2px solid #444 !important; box-shadow: inset -2px -2px 0px 0px #000, inset 2px 2px 0px 0px #555 !important; font-family: "Press Start 2P", cursive !important; color: #E0E0E0 !important; padding: 0.5rem !important; width: 100% !important; font-size: 12px !important; outline: none !important; -webkit-appearance: none !important; -moz-appearance: none !important; appearance: none !important; padding-right: 2rem !important;'
            }), 
            'weight': forms.NumberInput(attrs={
                'class': 'pixel-input',
                'placeholder': 'lbs',
                'style': 'background-color: #1c1c1c !important; border: 2px solid #444 !important; box-shadow: inset -2px -2px 0px 0px #000, inset 2px 2px 0px 0px #555 !important; font-family: "Press Start 2P", cursive !important; color: #E0E0E0 !important; padding: 0.5rem !important; width: 100% !important; font-size: 12px !important; outline: none !important; -webkit-appearance: none !important; -moz-appearance: none !important; appearance: none !important;'
            }), 
            'sex': forms.Select(attrs={
                'class': 'pixel-select',
                'style': 'background-color: #1c1c1c !important; border: 2px solid #444 !important; box-shadow: inset -2px -2px 0px 0px #000, inset 2px 2px 0px 0px #555 !important; font-family: "Press Start 2P", cursive !important; color: #E0E0E0 !important; padding: 0.5rem !important; width: 100% !important; font-size: 12px !important; outline: none !important; -webkit-appearance: none !important; -moz-appearance: none !important; appearance: none !important;'
            }),
            'sync_debounce_minutes': forms.NumberInput(attrs={
                'class': 'pixel-input',
                'placeholder': 'Sync debounce (minutes)',
                'style': 'background-color: #1c1c1c !important; border: 2px solid #444 !important; box-shadow: inset -2px -2px 0px 0px #000, inset 2px 2px 0px 0px #555 !important; font-family: "Press Start 2P", cursive !important; color: #E0E0E0 !important; padding: 0.5rem !important; width: 100% !important; font-size: 12px !important; outline: none !important; -webkit-appearance: none !important; -moz-appearance: none !important; appearance: none !important;',
                'min': '1',
                'max': '1440'
            }),
            'avatar': forms.FileInput(attrs={
                'class': 'pixel-file',
                'accept': 'image/*',
                'capture': 'user',
                'style': 'background-color: #1c1c1c !important; border: 2px solid #444 !important; box-shadow: inset -2px -2px 0px 0px #000, inset 2px 2px 0px 0px #555 !important; font-family: "Press Start 2P", cursive !important; color: #E0E0E0 !important; padding: 0.5rem !important; width: 100% !important; font-size: 12px !important; outline: none !important; -webkit-appearance: none !important; -moz-appearance: none !important; appearance: none !important;'
            })
        }


class SignUpForm(UserCreationForm):
    password1 = forms.CharField(
        label='Password',
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'pixel-input',
            'placeholder': 'Create a secure password',
            'style': 'background-color: #1c1c1c !important; border: 2px solid #444 !important; box-shadow: inset -2px -2px 0px 0px #000, inset 2px 2px 0px 0px #555 !important; font-family: "Press Start 2P", cursive !important; color: #E0E0E0 !important; padding: 0.5rem !important; width: 100% !important; font-size: 12px !important; outline: none !important; -webkit-appearance: none !important; -moz-appearance: none !important; appearance: none !important;'
        }),
        help_text=None,
    )


    password2 = forms.CharField(
        label='Password confirmation',
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'pixel-input',
            'placeholder': 'Confirm your password',
            'style': 'background-color: #1c1c1c !important; border: 2px solid #444 !important; box-shadow: inset -2px -2px 0px 0px #000, inset 2px 2px 0px 0px #555 !important; font-family: "Press Start 2P", cursive !important; color: #E0E0E0 !important; padding: 0.5rem !important; width: 100% !important; font-size: 12px !important; outline: none !important; -webkit-appearance: none !important; -moz-appearance: none !important; appearance: none !important;'
        }),
        help_text=None,
    )


    class Meta:
        model = User
        fields = ('username', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'pixel-input',
                'placeholder': 'Choose your gamer tag',
                'style': 'background-color: #1c1c1c !important; border: 2px solid #444 !important; box-shadow: inset -2px -2px 0px 0px #000, inset 2px 2px 0px 0px #555 !important; font-family: "Press Start 2P", cursive !important; color: #E0E0E0 !important; padding: 0.5rem !important; width: 100% !important; font-size: 12px !important; outline: none !important; -webkit-appearance: none !important; -moz-appearance: none !important; appearance: none !important;'
            })
        }

