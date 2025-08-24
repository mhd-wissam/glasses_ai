from django.urls import path
from .views import(
    OrderCreateView, 
    MyOrdersView, 
    OrderStatusUpdateView, 
    OrderUpdateView, 
    OrderDeleteView,
    StoreOrdersView,
    OrderDetailView
    )

urlpatterns = [
    path("create/", OrderCreateView.as_view(), name="order-create"),
    path("my-orders/", MyOrdersView.as_view(), name="my-orders"),
    path("<int:pk>/update-status/", OrderStatusUpdateView.as_view(), name="order-update-status"),
    path("<int:pk>/update/", OrderUpdateView.as_view(), name="order-update"),
    path("<int:pk>/delete/", OrderDeleteView.as_view(), name="order-delete"),
    path("store-orders/", StoreOrdersView.as_view(), name="store-orders"),
    path("<int:order_id>/detail/", OrderDetailView.as_view(), name="order-detail")
]
