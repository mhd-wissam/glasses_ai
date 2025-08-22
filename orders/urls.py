from django.urls import path
from .views import OrderCreateView, MyOrdersView, OrderStatusUpdateView

urlpatterns = [
    path("create/", OrderCreateView.as_view(), name="order-create"),
    path("my-orders/", MyOrdersView.as_view(), name="my-orders"),
    path("<int:pk>/update-status/", OrderStatusUpdateView.as_view(), name="order-update-status"),
]
