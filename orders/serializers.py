from rest_framework import serializers
from .models import Order, OrderItem
from glasses.models import Glasses
from glasses.serializers import GlassesDetailSerializer
from stores.serializers import StoreSerializer


class OrderItemSerializer(serializers.ModelSerializer):
    glasses = GlassesDetailSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = ["glasses", "quantity", "price"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    store = StoreSerializer(read_only=True)   # 👈 بيانات المتجر

    class Meta:
        model = Order
        fields = ["id", "store", "total_price", "status", "items", "created_at"]


# 👇 Serializer خاص بإنشاء الطلب
class OrderCreateSerializer(serializers.ModelSerializer):
    items = serializers.ListField(
        child=serializers.DictField(), write_only=True
    )

    class Meta:
        model = Order
        fields = ["id", "items"]

    def create(self, validated_data):
        request = self.context["request"]
        user = request.user
        items_data = validated_data.pop("items")

        store = None
        total_price = 0
        order_items = []

        for item in items_data:
            glasses = Glasses.objects.get(id=item["glasses_id"])
            if store is None:
                store = glasses.store
            elif glasses.store != store:
                raise serializers.ValidationError("⚠️ All items must be from the same store.")

            quantity = item["quantity"]
            price = glasses.price * quantity
            total_price += price

            order_items.append((glasses, quantity, price))

        # 🛒 إنشاء الطلب
        order = Order.objects.create(
            user=user,
            store=store,
            total_price=total_price,
            status="pending"
        )

        # ➕ إضافة العناصر
        for glasses, quantity, price in order_items:
            OrderItem.objects.create(
                order=order,
                glasses=glasses,
                quantity=quantity,
                price=price
            )

        return order


class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ["status"]

    def validate_status(self, value):
        # ✅ جلب كل القيم المسموحة من الموديل
        allowed_statuses = [choice[0] for choice in Order.STATUS_CHOICES]
        if value not in allowed_statuses:
            raise serializers.ValidationError(f"⚠️ Invalid status value. Must be one of: {allowed_statuses}")

        order = self.instance
        if order:
            current = order.status
            # ✅ transitions مبنية على statuses الحقيقية
            transitions = {
                "pending": ["confirmed"],
                "confirmed": ["shipped"],
                "shipped": ["delivered"],
                "delivered": []
            }
            if value not in transitions[current]:
                raise serializers.ValidationError(
                    f"⚠️ Invalid transition: Cannot move from '{current}' to '{value}'."
                )
        return value
