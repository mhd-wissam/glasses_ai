from rest_framework import serializers
from .models import Glasses, GlassesImage, Purpose
from users.models import Favorite   # 👈 موديل المفضلة

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
