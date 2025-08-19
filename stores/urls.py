from django.urls import path
from .views import StoreInfoView, ListStoresView

urlpatterns = [
    path("add-info/", StoreInfoView.as_view(), name="store-add-info"),
    path("list/", ListStoresView.as_view(), name="list-stores"),
]
