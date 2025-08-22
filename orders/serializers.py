from rest_framework import serializers
from .models import Order, OrderItem
from glasses.models import Glasses
from glasses.serializers import GlassesDetailSerializer
from stores.serializers import StoreSerializer
import re

class OrderItemSerializer(serializers.ModelSerializer):
    glasses = GlassesDetailSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = ["glasses", "quantity", "price"]

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    store = StoreSerializer(read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "store",
            "total_price",
            "status",
            "items",
            "recipient_name",      # ✅ جديد
            "recipient_phone",     # ✅ جديد
            "recipient_address",   # ✅ جديد
            "created_at"
        ]



# 👇 Serializer خاص بإنشاء الطلب
class OrderCreateSerializer(serializers.ModelSerializer):
    items = serializers.ListField(
        child=serializers.DictField(), write_only=True
    )

    # ✅ نخليهم مطلوبين
    recipient_name = serializers.CharField(required=True)
    recipient_phone = serializers.CharField(required=True)
    recipient_address = serializers.CharField(required=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "items",
            "recipient_name",
            "recipient_phone",
            "recipient_address"
        ]

    def validate_recipient_phone(self, value):
        """ ✅ تحقق أن رقم الهاتف يبدأ بـ 09 ويتكون من 10 أرقام """
        if not re.match(r"^09\d{8}$", value):
            raise serializers.ValidationError("⚠️ Recipient phone must be 10 digits and start with 09.")
        return value

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

        # 🛒 إنشاء الطلب مع بيانات المستلم
        order = Order.objects.create(
            user=user,
            store=store,
            total_price=total_price,
            status="pending",
            recipient_name=validated_data["recipient_name"],
            recipient_phone=validated_data["recipient_phone"],
            recipient_address=validated_data["recipient_address"],
        )

        for glasses, quantity, price in order_items:
            OrderItem.objects.create(order=order, glasses=glasses, quantity=quantity, price=price)

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

class OrderUpdateSerializer(serializers.ModelSerializer):
    items = serializers.ListField(
        child=serializers.DictField(), required=True, write_only=True
    )

    class Meta:
        model = Order
        fields = [
            "recipient_name",
            "recipient_phone",
            "recipient_address",
            "items",
        ]

    def validate_recipient_phone(self, value):
        if value and not re.match(r"^09\d{8}$", value):
            raise serializers.ValidationError("⚠️ Recipient phone must be 10 digits and start with 09.")
        return value

    def update(self, instance, validated_data):
        if instance.status != "pending":
            raise serializers.ValidationError("⚠️ Only pending orders can be modified.")

        # ✅ تحديث بيانات المستلم
        instance.recipient_name = validated_data.get("recipient_name", instance.recipient_name)
        instance.recipient_phone = validated_data.get("recipient_phone", instance.recipient_phone)
        instance.recipient_address = validated_data.get("recipient_address", instance.recipient_address)

        # ✅ مقارنة الـ Items
        items_data = validated_data.pop("items", [])
        old_items = {item.glasses.id: item for item in instance.items.all()}  
        new_items = {item["glasses_id"]: item for item in items_data}  

        total_price = 0

        # 1️⃣ تحديث أو إضافة العناصر
        for glasses_id, item in new_items.items():
            glasses = Glasses.objects.get(id=glasses_id)
            quantity = item.get("quantity", 1)
            price = glasses.price * quantity
            total_price += price

            if glasses_id in old_items:
                # تحديث الكمية لو تغيرت
                order_item = old_items[glasses_id]
                if order_item.quantity != quantity or order_item.price != price:
                    order_item.quantity = quantity
                    order_item.price = price
                    order_item.save()
            else:
                # إضافة عنصر جديد
                OrderItem.objects.create(
                    order=instance,
                    glasses=glasses,
                    quantity=quantity,
                    price=price
                )

        # 2️⃣ حذف العناصر اللي ما بعتهم المستخدم
        for glasses_id, order_item in old_items.items():
            if glasses_id not in new_items:
                order_item.delete()

        # 3️⃣ تحديث إجمالي السعر
        instance.total_price = total_price
        instance.save()
        return instance
