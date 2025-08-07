from django.urls import path
from . import views

urlpatterns = [
    path('category', views.CategoryView.as_view()),
    # menu items
    path('menu-items', views.MenuItemsView.as_view()),
    path('menu-items/<int:pk>', views.SingleMenuItemView.as_view()),
    
    # managers
    path('groups/manager/users', views.managers),
    path('groups/manager/users/<int:id>', views.delete_manager),
    
    # delivery crew
    path('groups/delivery-crew/users', views.delivery_crew),
    path('groups/delivery-crew/users/<int:id>', views.delete_delivery_crew_member),
    
    # cart
    path('cart/menu-items', views.cart_view),
    
    # order
    path('orders', views.order_view),
    path('orders/<int:orderId>', views.single_order_view),
]