from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied

from .models import Order
from .serializers import (
    OrderSerializer,
    OrderCreateSerializer,
    OrderStatusUpdateSerializer
)


# 🛒 إنشاء طلبية جديدة
class OrderCreateView(generics.CreateAPIView):
    serializer_class = OrderCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        order = serializer.save()

        return Response({
            "message": "✅ Order created successfully",
            "order": OrderSerializer(order, context={"request": request}).data
        }, status=status.HTTP_201_CREATED)


# 📦 عرض طلباتي
class MyOrdersView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Order.objects
            .filter(user=self.request.user)
            .prefetch_related("items__glasses", "store")
        )


# 🔄 تحديث حالة الطلب
class OrderStatusUpdateView(generics.UpdateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderStatusUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def update(self, request, *args, **kwargs):
        order = self.get_object()

        # ✅ تحقق أن المستخدم Store Owner أو Admin
        if request.user.role not in ["store_owner", "admin"]:
            raise PermissionDenied("⚠️ You must be a store owner or admin to update orders.")

        # ✅ لو كان Store Owner، تأكد أنه صاحب المتجر
        if request.user.role == "store_owner" and request.user != order.store.owner:
            raise PermissionDenied("⚠️ You are not the owner of this store.")

        serializer = self.get_serializer(order, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            "message": "✅ Order status updated successfully",
            "order": OrderSerializer(order, context={"request": request}).data
        }, status=status.HTTP_200_OK)
