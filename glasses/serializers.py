# glasses/serializers.py
from rest_framework import serializers
from .models import Glasses, GlassesImage, Purpose

class GlassesImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlassesImage
        fields = ['id', 'image']

class GlassesSerializer(serializers.ModelSerializer):
    images = GlassesImageSerializer(many=True, read_only=True)

    purposes = serializers.SlugRelatedField(
        many=True,
        slug_field='name',
        queryset=Purpose.objects.all(),
        required=False
    )

    class Meta:
        model = Glasses
        fields = '__all__'

class GlassesDetailSerializer(serializers.ModelSerializer):
    images = GlassesImageSerializer(many=True, read_only=True)
    purposes = serializers.SlugRelatedField(
        many=True,
        slug_field='name',
        queryset=Purpose.objects.all(),
        required=False
    )

    class Meta:
        model = Glasses
        fields = '__all__'

