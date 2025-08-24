from rest_framework import serializers
from users.models import Favorite   # 👈 موديل المفضلة
from .models import Glasses, GlassesImage, Purpose, GlassesPurpose
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

            # هنا نعمل set مباشرة → تحذف القديم وتضيف الجديد
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
                    GlassesImage.objects.create(glasses=instance, image=img)

            # تحديث القديمة
            for i, img in enumerate(new_images[:len(old_images)]):
                old_images[i].image = img
                old_images[i].save()

        return instance