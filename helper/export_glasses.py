import os
import django
import pandas as pd

# ✅ اضبط Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from glasses.models import Glasses

def export_glasses():
    data = []

    for g in Glasses.objects.all().prefetch_related("purposes", "images").select_related("store"):
        purposes = ", ".join([p.name for p in g.purposes.all()])
        images = ", ".join([img.image.url for img in g.images.all()])

        data.append({
            "ID": g.id,
            "Shape": g.shape,
            "Material": g.material,
            "Size": g.size,
            "Gender": g.gender,
            "Tone": g.tone,
            "Color": g.color,
            "Weight": g.weight,
            "Manufacturer": g.manufacturer,
            "Price": g.price,
            "Store": g.store.store_name if g.store else None,
            "Purposes": purposes,
            "Images": images,
            "3D_Model": g.model_3d.url if g.model_3d else None,
        })

    df = pd.DataFrame(data)
    file_path = "glasses_export.xlsx"
    df.to_excel(file_path, index=False)
    print(f"✅ تم تصدير البيانات إلى {file_path}")

if __name__ == "__main__":
    export_glasses()
