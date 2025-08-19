from django.db import models
from django.core.validators import RegexValidator
from users.models import CustomUser

phone_validator = RegexValidator(
    regex=r'^09\d{8}$',
    message="Phone number must be exactly 10 digits and start with 09."
)

class Store(models.Model):
    owner = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="store")
    store_name = models.CharField(max_length=255, unique=True)
    phone = models.CharField(max_length=10, validators=[phone_validator], unique=True)
    location_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    image = models.ImageField(upload_to="store_images/", null=True, blank=True)
    
    def __str__(self):
        return self.store_name
