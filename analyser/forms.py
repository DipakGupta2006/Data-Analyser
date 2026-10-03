import os
from django import forms
from .models import Dataset

ALLOWED_EXTENSIONS = [".csv", ".xlsx", ".json"]
MAX_SIZE_MB = 15


class DatasetForm(forms.ModelForm):
    class Meta:
        model = Dataset
        fields = ["name", "file"]

    def clean_file(self):
        file = self.cleaned_data["file"]

        ext = os.path.splitext(file.name)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise forms.ValidationError("File extension allowed: " + ", ".join(ALLOWED_EXTENSIONS))

        if file.size == 0:
            raise forms.ValidationError("File size cannot be zero.")

        if file.size > MAX_SIZE_MB * 1024 * 1024:
            raise forms.ValidationError(f"File size cannot exceed {MAX_SIZE_MB} MB.")

        return file