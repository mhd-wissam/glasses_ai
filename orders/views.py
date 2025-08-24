from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied

from .models import Order
from .serializers import (
    OrderSerializer,
    OrderCreateSerializer,
    OrderStatusUpdateSerializer,
    OrderUpdateSerializer
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
            "message": "Order created successfully",
            "order": OrderSerializer(order, context={"request": request}).data
        }, status=status.HTTP_201_CREATED)


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

class OrderUpdateView(generics.UpdateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def update(self, request, *args, **kwargs):
        order = self.get_object()

        # تأكد أنه طلب للمستخدم نفسه
        if order.user != request.user:
            raise PermissionDenied("⚠️ You cannot edit this order.")

        serializer = self.get_serializer(order, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()

        return Response({
            "message": "✅ Order updated successfully",
            "order": OrderSerializer(order, context={"request": request}).data
        }, status=status.HTTP_200_OK)
    
class OrderDeleteView(generics.DestroyAPIView):
    queryset = Order.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def destroy(self, request, *args, **kwargs):
        order = self.get_object()

        # تحقق أنه طلب المستخدم نفسه
        if order.user != request.user:
            raise PermissionDenied("⚠️ You cannot delete this order.")

        # تحقق من حالة الطلب
        if order.status != "pending":
            raise PermissionDenied("⚠️ Cannot delete order unless it is still pending.")

        order.delete()
        return Response({"message": "🗑️ Order deleted successfully."})    

class StoreOrdersView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # 👮 السماح فقط لصاحب المتجر أو الأدمن
        if user.role not in ["store_owner", "admin"]:
            raise PermissionDenied("⚠️ Only store owners or admins can view store orders.")

        if user.role == "admin":
            # الادمن ممكن يشوف كل الطلبات
            return Order.objects.all().select_related("store", "user").prefetch_related("items__glasses")

        if not hasattr(user, "store"):
            raise PermissionDenied("⚠️ You don't have a store.")

        # صاحب المتجر → طلبات متجره فقط
        return (
            Order.objects.filter(store=user.store)
            .select_related("store", "user")
            .prefetch_related("items__glasses")
            .order_by("-created_at")
        )
    
class OrderDetailView(generics.RetrieveAPIView):
    queryset = Order.objects.all().select_related("store", "user").prefetch_related("items__glasses")
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "id"
    lookup_url_kwarg = "order_id"

    def get_object(self):
        order = super().get_object()
        user = self.request.user

        # ✅ Admin → يشوف الكل
        if user.role == "admin":
            return order

        # ✅ Customer → بس طلباته
        if order.user == user:
            return order

        # ✅ Store Owner → بس الطلبات بمتجره
        if user.role == "store_owner" and hasattr(user, "store") and order.store == user.store:
            return order

        # ❌ لو غير هيك
        raise PermissionDenied("⚠️ You are not allowed to view this order.")
