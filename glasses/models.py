# from django.db import models

# # Create your models here.

# class Glasses(models.Model):
#     frame_id = models.CharField(max_length=100, unique=True)
#     material = models.CharField(max_length=100)
#     rim = models.CharField(max_length=50)
#     shape = models.CharField(max_length=50)
#     size = models.CharField(max_length=50)
#     gender = models.CharField(max_length=10)
#     weight = models.FloatField(null=True, blank=True)
#     frame_width = models.IntegerField()
#     bridge = models.IntegerField()
#     lens_width = models.IntegerField()
#     lens_height = models.IntegerField()
#     temple_length = models.IntegerField()
#     model_3d = models.FileField(upload_to='glasses_models/', null=True, blank=True)
#     def __str__(self):
#         return f"{self.frame_id} - {self.shape}"

from django.db import models

class Purpose(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = "Purpose"
        verbose_name_plural = "Purposes"

    def __str__(self):
        return self.name


class Glasses(models.Model):

    class Material(models.TextChoices):
        ACETATE = "Acetate"
        PLASTIC = "Plastic"
        METAL = "Metal"
        STAINLESS = "Stainless Steel"
        TITANIUM = "Titanium"
        TR90 = "TR90"
        MIXED = "Mixed"
        CARBON = "Carbon Fiber"
        OTHER = "Other"

    class Shape(models.TextChoices):
        RECTANGLE = "Rectangle"
        SQUARE = "Square"
        ROUND = "Round"
        OVAL = "Oval"
        CAT_EYE = "Cat-Eye"
        AVIATOR = "Aviator"
        GEOMETRIC = "Geometric"
        BROWLINE = "Browline"
        RIMLESS = "Rimless"
        WAYFARER = "Wayfarer"
        BUTTERFLY = "Butterfly"
        SHIELD = "Shield"
        CLUBMASTER = "Clubmaster"
        HEXAGONAL = "Hexagonal / Octagonal"
        OTHER = "Other"

    class Size(models.TextChoices):
        SMALL = "Small"
        MEDIUM = "Medium"
        LARGE = "Large"
        EXTRA_LARGE = "Extra Large"

    class Gender(models.TextChoices):
        MALE = "Male"
        FEMALE = "Female"
        UNISEX = "Unisex"
        KIDS = "Kids"

    class Tone(models.TextChoices):
        DARK = "Dark"
        MEDIUM = "Medium"
        LIGHT = "Light"

    class GeneralColor(models.TextChoices):
        BLACK = "Black"
        BLUE = "Blue"
        RED = "Red"
        GREEN = "Green"
        PURPLE = "Purple"
        GRAY = "Gray"
        BROWN = "Brown"
        GOLD = "Gold"
        OLIVE = "Olive"
        WHITE = "White"
        PINK = "Pink"
        SILVER = "Silver"
        BEIGE = "Beige"
        PEACH = "Peach"

    frame_id = models.CharField(max_length=100, unique=True)
    material = models.CharField(max_length=50, choices=Material.choices)
    rim = models.CharField(max_length=50)
    shape = models.CharField(max_length=50, choices=Shape.choices)
    size = models.CharField(max_length=20, choices=Size.choices)
    gender = models.CharField(max_length=10, choices=Gender.choices)
    tone = models.CharField(max_length=10, choices=Tone.choices)
    color = models.CharField(max_length=20, choices=GeneralColor.choices)

    frame_width = models.IntegerField()
    bridge = models.IntegerField()
    lens_width = models.IntegerField()
    lens_height = models.IntegerField()
    temple_length = models.IntegerField()

    weight = models.FloatField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    model_3d = models.FileField(upload_to='glasses_models/', null=True, blank=True)

    purposes = models.ManyToManyField(
        Purpose,
        through='GlassesPurpose',
        related_name='glasses'
    )

    def __str__(self):
        return f"{self.frame_id} - {self.shape}"


class GlassesPurpose(models.Model):

    glasses = models.ForeignKey(Glasses, on_delete=models.CASCADE)
    purpose = models.ForeignKey(Purpose, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('glasses', 'purpose') 
        verbose_name = "Glasses-Purpose"
        verbose_name_plural = "Glasses-Purposes"

    def __str__(self):
        return f"{self.glasses.frame_id} ↔ {self.purpose.name}"


class GlassesImage(models.Model):
    glasses = models.ForeignKey(Glasses, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='glasses_images/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.glasses.frame_id}"
