from django.db import models
from django.contrib.auth.models import User
import os

class Dataset(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="datasets")
    name = models.CharField(max_length=250)
    file = models.FileField(upload_to="datasets/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    @property
    def extension(self):
        return os.path.splitext(self.file.name)[1].lstrip(".").upper()

    