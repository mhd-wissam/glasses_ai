import os
import django
import pandas as pd
import numpy as np

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from glasses.models import Glasses

file_path = r'C:\Users\LEGION\Desktop\sample_project_1\glasses_cleaned.xlsx'
df = pd.read_excel(file_path)

df = df.replace({np.nan: None})

Glasses.objects.all().delete()

for index, row in df.iterrows():
    Glasses.objects.create(
        frame_id=row['Frame ID'],
        material=row['Material'],
        rim=row['Rim'],
        shape=row['Shape'],
        size=row['Size'],
        gender=row['Gender'],
        weight=row['Weight (g)'],
        frame_width=row['Frame Width (mm)'],
        bridge=row['Bridge (mm)'],
        lens_width=row['Lens Width (mm)'],
        lens_height=row['Lens Height (mm)'],
        temple_length=row['Temple Length (mm)'],
    )

print("تم إدخال البيانات بنجاح إلى قاعدة البيانات")
