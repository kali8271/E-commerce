from django import forms
from .models import Customer, Review, ProductQuestion

class SignupForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, min_length=6)
    class Meta:
        model = Customer
        fields = ['first_name', 'last_name', 'phone', 'email', 'password']
        widgets = {
            'password': forms.PasswordInput(),
        }

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if len(phone) < 10:
            raise forms.ValidationError('Phone Number must be 10 char Long')
        return phone

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name')
        if len(first_name) < 4:
            raise forms.ValidationError('First Name must be 4 char long or more')
        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name')
        if len(last_name) < 4:
            raise forms.ValidationError('Last Name must be 4 char long or more')
        return last_name

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if len(email) < 5:
            raise forms.ValidationError('Email must be 5 char long')
        if Customer.objects.filter(email=email).exists():
            raise forms.ValidationError('Email Address Already Registered..')
        return email

class LoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)

class CustomerProfileForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['first_name', 'last_name', 'phone', 'email']

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'review']
        widgets = {
            'rating': forms.Select(choices=[(i, i) for i in range(1, 6)]),
            'review': forms.Textarea(attrs={'rows': 3}),
        }

class ProductQuestionForm(forms.ModelForm):
    class Meta:
        model = ProductQuestion
        fields = ['question']
        widgets = {
            'question': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Ask a question about this product...'}),
        } 