from django import forms
from django.utils import timezone
from .models import WeightRecord, WeightGoal, WeightUnit

class WeightRecordForm(forms.ModelForm):
    unit = forms.ModelChoiceField(
        queryset=WeightUnit.objects.filter(symbol__in=['lbs', 'kg']),
        widget=forms.HiddenInput(),
        required=True
    )

    class Meta:
        model = WeightRecord
        fields = ['weight', 'date', 'notes', 'unit']
        widgets = {
            'weight': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'min': '0',
                'placeholder': 'Enter weight'
            }),
            'date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': False,
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional notes about this weight record',
                'style': 'max-width: 100%;'
            })
        }

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        
        # Make date field optional
        self.fields['date'].required = False
        
        # Set up initial unit selection based on instance or default to lbs
        if self.instance.pk and hasattr(self.instance, 'unit'):
            self.fields['unit'].initial = self.instance.unit
        else:
            # Default to lbs if available, otherwise use the first available unit
            try:
                lbs_unit = WeightUnit.objects.get(symbol='lbs')
                self.fields['unit'].initial = lbs_unit
            except WeightUnit.DoesNotExist:
                # If lbs doesn't exist, use the first available unit
                first_unit = WeightUnit.objects.first()
                if first_unit:
                    self.fields['unit'].initial = first_unit

    def clean_date(self):
        date = self.cleaned_data.get('date')
        if not date:
            return timezone.now().date()
        return date

    def clean_unit(self):
        unit = self.cleaned_data.get('unit')
        if not unit:
            # If no unit is provided, default to lbs
            try:
                return WeightUnit.objects.get(symbol='lbs')
            except WeightUnit.DoesNotExist:
                # If lbs doesn't exist, use the first available unit
                return WeightUnit.objects.first()
        return unit

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.user = self.user
            
        if commit:
            instance.save()
        return instance


class WeightGoalForm(forms.ModelForm):
    start_unit = forms.ModelChoiceField(
        queryset=WeightUnit.objects.filter(symbol__in=['lbs', 'kg']),
        widget=forms.HiddenInput(),
        required=True
    )
    target_unit = forms.ModelChoiceField(
        queryset=WeightUnit.objects.filter(symbol__in=['lbs', 'kg']),
        widget=forms.HiddenInput(),
        required=True
    )

    class Meta:
        model = WeightGoal
        fields = ['start_weight', 'start_unit', 'target_weight', 'target_unit', 'target_date']
        widgets = {
            'start_weight': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'min': '0',
                'placeholder': 'Enter starting weight'
            }),
            'target_weight': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'min': '0',
                'placeholder': 'Enter target weight'
            }),
            'target_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'min': timezone.now().date().isoformat()
            })
        }

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        
        # Set up initial unit selection based on instance or default to lbs
        if self.instance.pk:
            if hasattr(self.instance, 'start_unit'):
                self.fields['start_unit'].initial = self.instance.start_unit
            if hasattr(self.instance, 'target_unit'):
                self.fields['target_unit'].initial = self.instance.target_unit
        else:
            # Default to lbs if available, otherwise use the first available unit
            try:
                lbs_unit = WeightUnit.objects.get(symbol='lbs')
                self.fields['start_unit'].initial = lbs_unit
                self.fields['target_unit'].initial = lbs_unit
            except WeightUnit.DoesNotExist:
                # If lbs doesn't exist, use the first available unit
                first_unit = WeightUnit.objects.first()
                if first_unit:
                    self.fields['start_unit'].initial = first_unit
                    self.fields['target_unit'].initial = first_unit

    def clean_target_date(self):
        target_date = self.cleaned_data['target_date']
        if target_date < timezone.now().date():
            raise forms.ValidationError("Target date cannot be in the past")
        return target_date

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.user = self.user
        if commit:
            instance.save()
        return instance 