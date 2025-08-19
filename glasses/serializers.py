from rest_framework import serializers
from .models import Glasses, GlassesImage, Purpose


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
    store = serializers.CharField(source="store.store_name", read_only=True)  # 👈 يجيب اسم المتجر

    class Meta:
        model = Glasses
        fields = '__all__'

class GlassesDetailSerializer(serializers.ModelSerializer):
    images = GlassesImageSerializer(many=True, read_only=True)
    purposes = PurposeSerializer(many=True, read_only=True)  # 👈 يعرض id + name
    store_name = serializers.CharField(source="store.store_name", read_only=True)

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
        ]
