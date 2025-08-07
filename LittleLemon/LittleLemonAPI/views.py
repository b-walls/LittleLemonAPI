import datetime
from decimal import Decimal
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework import generics, status
from rest_framework.response import Response
from django.contrib.auth.models import User, Group
from rest_framework.permissions import IsAuthenticated
from .models import MenuItem, Category, Cart, Order, OrderItem
from .serializers import MenuItemSerializer, CategorySerializer, UserSerializer, CartSerializer, OrderSerializer, OrderItemSerializer
from .permissions import IsManager, IsDeliveryCrew

# Menu Items
class CategoryView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    
class MenuItemsView(generics.ListCreateAPIView):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        else:
            return [IsManager()]

class SingleMenuItemView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer
    
    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        else:
            return [IsManager()]

# Group Management
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated, IsManager])
def managers(request):
    managers = Group.objects.get(name="Manager")
    if request.method == 'GET':
        users = managers.user_set.all()
        serialized_data = UserSerializer(users, many=True)
        return Response(serialized_data.data, status=status.HTTP_200_OK)
    elif request.method == 'POST':
        username = request.data['username']
        user = get_object_or_404(User, username=username)
        managers.user_set.add(user)
        return Response(status=status.HTTP_201_CREATED)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsManager])
def delete_manager(request, id):
    managers = Group.objects.get(name="Manager")
    user = get_object_or_404(User, id=id)
    managers.user_set.remove(user)
    return Response(status=status.HTTP_200_OK)

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated, IsManager])
def delivery_crew(request):
    delivery_crew = Group.objects.get(name="Delivery crew")
    if request.method == 'GET':
        users = delivery_crew.user_set.all()
        serialized_data = UserSerializer(users, many=True)
        return Response(serialized_data.data, status.HTTP_200_OK)
    elif request.method == 'POST':
        username = request.data['username']
        user = get_object_or_404(User, username=username)
        delivery_crew.user_set.add(user)
        return Response(status=status.HTTP_201_CREATED)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsManager])
def delete_delivery_crew_member(request, id):
    delivery_crew = Group.objects.get(name="Delivery crew")
    user = get_object_or_404(User, id=id)
    delivery_crew.user_set.remove(user)
    return Response(status=status.HTTP_200_OK)

# Carts
@api_view(['GET', 'POST', 'DELETE'])
@permission_classes([IsAuthenticated])
def cart_view(request):
    user = request.user
    if request.method == 'GET':
        cart_items = Cart.objects.filter(user=user)
        serialized_data = CartSerializer(cart_items, many=True)
        return Response(serialized_data.data, status=status.HTTP_200_OK)
    
    if request.method == 'POST':
        menu_item_id = request.data['menu-item']
        menu_item = MenuItem.objects.get(id=menu_item_id)
        # increment cart object for this menu item if exists
        try:
            cart_item = Cart.objects.get(user=user, menuitem=menu_item)
            cart_item.quantity += 1
            cart_item.price += cart_item.unit_price
            cart_item.save()
        # create a new cart object
        except Cart.DoesNotExist:
            cart_item = Cart(user=user, 
                             menuitem=menu_item, 
                             quantity=1, 
                             unit_price=menu_item.price, 
                             price=menu_item.price)
            cart_item.save()
        return Response(status=status.HTTP_201_CREATED)
    
    if request.method == 'DELETE':
        Cart.objects.filter(user=user).delete()
        return Response(status=status.HTTP_200_OK)
    
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def order_view(request):
    user = request.user
    # manager requests
    if user.groups.filter(name="Manager").exists():
        if request.method == 'GET':
            orders = Order.objects.all()
            serialized_data = OrderSerializer(orders, many=True)
            return Response(serialized_data.data, status=status.HTTP_200_OK)

    # delivery crew requests
    elif user.groups.filter(name="Delivery crew").exists():
        if request.method == 'GET':
            orders = Order.objects.filter(delivery_crew=user)
            serialized_data = OrderSerializer(orders, many=True)
            return Response(serialized_data.data, status=status.HTTP_200_OK)
        
    # customer requests
    else:
        if request.method == 'GET':
            # gets all user orders
            orders = Order.objects.filter(user=user)
            serialized_data = OrderSerializer(orders, many=True)
            return Response(serialized_data.data, status=status.HTTP_200_OK)
        
        if request.method == 'POST':
            # transfers user cart into an order and discards the cart
            user_cart = Cart.objects.filter(user=user)
            user_order = Order(user=user, total=Decimal("0.00"), date=datetime.date.today())
            user_order.save()
            for cart_item in user_cart:
                order_item = OrderItem(order=user_order, 
                                       menuitem=cart_item.menuitem, 
                                       quantity=cart_item.quantity,
                                       unit_price=cart_item.unit_price,
                                       price=cart_item.price)
                user_order.total += order_item.price
                order_item.save()
            user_cart.delete()
            return Response({"detail": "Order created."},status=status.HTTP_201_CREATED)
    
    return Response(status=status.HTTP_401_UNAUTHORIZED)

@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def single_order_view(request, orderId):
    user = request.user
    order = Order.objects.get(id=orderId)
    # manager requests
    if user.groups.filter(name="Manager").exists():
        if request.method == 'PUT' or request.method == 'PATCH':
            # verify delivery status and patch
            delivery_status = request.data.get('status')
            if delivery_status is not None:
                order.status = delivery_status
                
            # verify delivery id and patch
            delivery_id = request.data.get('delivery_id')
            if delivery_id is not None:
                delivery_crew_member = User.objects.get(id=delivery_id)
                # checks if valid delivery crew
                if delivery_crew_member.groups.filter(name="Delivery crew").exists():
                    order.delivery_crew = delivery_crew_member
                else:
                    return Response({"detail": "Delivery crew id is invalid."}, status=status.HTTP_400_BAD_REQUEST)
    
            order.save()
            return Response({"detail": "Order updated."}, status=status.HTTP_200_OK)

        elif request.method == 'DELETE':
            # deletes the order
            order.delete()
            return Response({"detail": "Order deleted."}, status=status.HTTP_200_OK)
            
    # delivery crew requests
    elif user.groups.filter(name="Delivery crew").exists():
        # update delivery status
        if request.method == 'PATCH':
            delivery_status = request.data.get('status')
            if delivery_status is not None:
                order.status = delivery_status
                order.save()
                return Response({"detail": "Status updated."}, status=status.HTTP_200_OK)
            else:
                return Response({"detail": "Bad request."}, status=status.HTTP_400_BAD_REQUEST)
    else:
        if request.method == 'GET':
            if order.user == user:
                serialized_data = OrderSerializer(order)
                return Response(serialized_data.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_401_UNAUTHORIZED)
    
    return Response(status=status.HTTP_401_UNAUTHORIZED)