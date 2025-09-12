
from django import forms

class GarminConnectForm(forms.Form):
    garmin_email = forms.EmailField(
        label='Garmin Email',
        widget=forms.EmailInput(attrs={
            'class': 'pixel-input',
            'placeholder': 'your.garmin@email.com',
            'style': 'background-color: #1c1c1c !important; border: 2px solid #444 !important; box-shadow: inset -2px -2px 0px 0px #000, inset 2px 2px 0px 0px #555 !important; font-family: "Press Start 2P", cursive !important; color: #E0E0E0 !important; padding: 0.5rem !important; width: 100% !important; font-size: 12px !important; outline: none !important; -webkit-appearance: none !important; -moz-appearance: none !important; appearance: none !important;'
        })
    )
    garmin_password = forms.CharField(
        label='Garmin Password',
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'pixel-input',
            'placeholder': 'Enter your Garmin password',
            'style': 'background-color: #1c1c1c !important; border: 2px solid #444 !important; box-shadow: inset -2px -2px 0px 0px #000, inset 2px 2px 0px 0px #555 !important; font-family: "Press Start 2P", cursive !important; color: #E0E0E0 !important; padding: 0.5rem !important; width: 100% !important; font-size: 12px !important; outline: none !important; -webkit-appearance: none !important; -moz-appearance: none !important; appearance: none !important;'
        })
    )