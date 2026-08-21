"""
URL configuration for main project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from bookings.views import (
    home_view, 
    about_view, 
    login_view, 
    register_view, 
    logout_view, 
    book_accommodation_view, 
    contact_view, 
    admin_dashboard_view,
    mpesa_callback_view,
    update_room_status_view  # Imported the new status modification view
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home_view, name='home'),
    path('about/', about_view, name='about'),
    path('contact/', contact_view, name='contact'),
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', logout_view, name='logout'),
    path('book/', book_accommodation_view, name='book_room'),
    path('console/', admin_dashboard_view, name='admin_dashboard'),
    path('mpesa/callback/', mpesa_callback_view, name='mpesa_callback'),
    
    # Route for updating room status via the admin control panel
    path('console/room/update/<int:room_id>/', update_room_status_view, name='update_room_status'),
]