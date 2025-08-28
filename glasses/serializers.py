from rest_framework import serializers
from users.models import Favorite   # 👈 موديل المفضلة
from .models import Glasses, GlassesImage, Purpose, GlassesPurpose
from rembg import remove
from PIL import Image
import io
from django.core.files.base import ContentFile

class GlassesImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlassesImage
        fields = ["id", "image"]


class PurposeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Purpose
        fields = ["id", "name"]


class GlassesSerializer(serializers.ModelSerializer):
    images = GlassesImageSerializer(many=True, read_only=True)
    purposes = serializers.SlugRelatedField(
        many=True,
        slug_field='name',
        queryset=Purpose.objects.all(),
        required=False
    )
    favorite = serializers.SerializerMethodField()  # 👈 حقل المفضلة

    class Meta:
        model = Glasses
        fields = '__all__'   # أو حدد الحقول إذا حابب

    def get_favorite(self, obj):
        request = self.context.get('request', None)
        if request and request.user.is_authenticated:
            return Favorite.objects.filter(
                user=request.user, glasses=obj, is_favorite=True
            ).exists()
        return False


class GlassesDetailSerializer(serializers.ModelSerializer):
    images = GlassesImageSerializer(many=True, read_only=True)
    purposes = PurposeSerializer(many=True, read_only=True)  
    store_name = serializers.CharField(source="store.store_name", read_only=True)
    favorite = serializers.SerializerMethodField()  # 👈 نضيفه هنا أيضًا

    class Meta:
        model = Glasses
        fields = [
            "id",
            "shape",
            "material",
            "size",
            "gender",
            "tone",
            "color",
            "weight",
            "manufacturer",
            "price",
            "model_3d",
            "store_name",
            "images",
            "purposes",
            "favorite",  # 👈 ضروري
        ]

    def get_favorite(self, obj):
        request = self.context.get("request", None)
        if request and request.user.is_authenticated:
            return Favorite.objects.filter(
                user=request.user, glasses=obj, is_favorite=True
            ).exists()
        return False

class GlassesUpdateSerializer(serializers.ModelSerializer):
    purposes = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )
    images = serializers.ListField(
        child=serializers.ImageField(), write_only=True, required=False
    )

    class Meta:
        model = Glasses
        fields = [
            "shape", "material", "size", "gender", "tone", "color",
            "weight", "manufacturer", "price", "purposes", "images"
        ]

    def update(self, instance, validated_data):
        # ✅ تحديث الحقول العادية
        for attr, value in validated_data.items():
            if attr not in ["purposes", "images"]:
                setattr(instance, attr, value)

        instance.save()

        # ✅ تحديث الـ purposes
        if "purposes" in validated_data:
            purpose_names = validated_data["purposes"]
            purpose_objs = []
            for p_name in purpose_names:
                try:
                    purpose_obj, _ = Purpose.objects.get_or_create(name=p_name.strip())
                    purpose_objs.append(purpose_obj)
                except Purpose.DoesNotExist:
                    continue
            instance.purposes.set(purpose_objs)

        # ✅ تحديث الصور
        if "images" in validated_data:
            new_images = validated_data["images"]
            old_images = list(instance.images.all())

            # حذف الزائد
            if len(new_images) < len(old_images):
                to_delete = old_images[len(new_images):]
                for img in to_delete:
                    img.delete()

            # إضافة الجديد
            if len(new_images) > len(old_images):
                to_add = new_images[len(old_images):]
                for img in to_add:
                    # 🔹 تحويل الصورة إلى PNG مع إزالة الخلفية
                    input_img = Image.open(img)
                    output_img = remove(input_img).convert("RGBA")

                    img_io = io.BytesIO()
                    output_img.save(img_io, format="PNG")
                    img_content = ContentFile(img_io.getvalue(), name=f"{img.name.split('.')[0]}.png")

                    GlassesImage.objects.create(glasses=instance, image=img_content)

            # تحديث القديمة
            for i, img in enumerate(new_images[:len(old_images)]):
                # 🔹 تحويل الصورة إلى PNG مع إزالة الخلفية
                input_img = Image.open(img)
                output_img = remove(input_img).convert("RGBA")

                img_io = io.BytesIO()
                output_img.save(img_io, format="PNG")
                img_content = ContentFile(img_io.getvalue(), name=f"{img.name.split('.')[0]}.png")

                old_images[i].image.save(img_content.name, img_content, save=True)

        return instance
    
class GlassesRecommendationSerializer(serializers.ModelSerializer):
    images = GlassesImageSerializer(many=True, read_only=True)
    purposes = PurposeSerializer(many=True, read_only=True)
    store_name = serializers.CharField(source="store.store_name", read_only=True)
    favorite = serializers.SerializerMethodField()

    # 👇 الحقول القادمة من محرك KBS
    score = serializers.IntegerField(read_only=True)
    match_percentage = serializers.FloatField(read_only=True)
    reasons = serializers.ListField(child=serializers.CharField(), read_only=True)

    class Meta:
        model = Glasses
        fields = [
            "id",
            "shape",
            "material",
            "size",
            "gender",
            "tone",
            "color",
            "weight",
            "manufacturer",
            "price",
            "model_3d",
            "store_name",
            "images",
            "purposes",
            "favorite",
            "score",
            "match_percentage",
            "reasons",
        ]

    def get_favorite(self, obj):
        request = self.context.get("request", None)
        if request and request.user.is_authenticated:
            return Favorite.objects.filter(
                user=request.user, glasses=obj, is_favorite=True
            ).exists()
        return False
    
class GlassesCreateSerializer(serializers.ModelSerializer):
    purposes = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )
    images = serializers.ListField(
        child=serializers.ImageField(), write_only=True, required=False
    )

    # 🔹 للعرض بعد الحفظ
    images_data = GlassesImageSerializer(source="images", many=True, read_only=True)
    purposes_data = PurposeSerializer(source="purposes", many=True, read_only=True)
    store_name = serializers.CharField(source="store.store_name", read_only=True)

    class Meta:
        model = Glasses
        fields = [
            "id",
            "shape", "material", "size", "gender", "tone", "color",
            "weight", "manufacturer", "price",
            "purposes", "images",       # ← للإنشاء فقط
            "images_data", "purposes_data", "store_name"  # ← للعرض
        ]

    def create(self, validated_data):
        purposes_data = validated_data.pop("purposes", [])
        images_data = validated_data.pop("images", [])
        user = self.context["request"].user

        if not hasattr(user, "store"):
            raise serializers.ValidationError("Only store owners can add glasses.")

        glasses = Glasses.objects.create(store=user.store, **validated_data)

        # 🔹 إضافة Purposes
        for p_name in purposes_data:
            try:
                purpose_obj = Purpose.objects.get(name__iexact=p_name.strip())
                GlassesPurpose.objects.get_or_create(glasses=glasses, purpose=purpose_obj)
            except Purpose.DoesNotExist:
                continue

        # 🔹 معالجة الصور
        for img in images_data:
            input_img = Image.open(img)
            output_img = remove(input_img).convert("RGBA")

            img_io = io.BytesIO()
            output_img.save(img_io, format="PNG")
            img_content = ContentFile(img_io.getvalue(), name=f"{img.name.split('.')[0]}.png")

            GlassesImage.objects.create(glasses=glasses, image=img_content)

        return glasses
