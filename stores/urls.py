from django.urls import path
from .views import StoreInfoView, ListStoresView, MyStoreInfoView

urlpatterns = [
    path("add-info/", StoreInfoView.as_view(), name="store-add-info"),
    path("list/", ListStoresView.as_view(), name="list-stores"),
    path("my-store/", MyStoreInfoView.as_view(), name="store-info"),
]
