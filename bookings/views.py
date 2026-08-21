from django.shortcuts import render, redirect, get_object_or_404
from django.db import connection
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
import requests
import json
from .mpesa import initiate_stk_push

# Replace these with your actual Supabase Project API credentials
SUPABASE_URL = "https://lfrgzhtlqnlljwvwiyqo.supabase.co"  
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imxmcmd6aHRscW5sbGp3dndpeXFvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODIwMzY1NTUsImV4cCI6MjA5NzYxMjU1NX0.GqmjJ3smXgtNY76w8lCyUrKu3emTPMb6Ugx97DMfTwQ"


# ==========================================
# 1. PUBLIC VIEWS (Anyone can access)
# ==========================================

def home_view(request):
    """
    Fetches available rooms from Supabase and applies dynamic guest capacity filtering
    whenever a user clicks "Check Availability" on the home layout.
    """
    guest_capacity = request.GET.get('guests')
    
    query = "SELECT id, name, base_price, max_adults, status FROM room_types"
    params = []
    
    # Filter catalog based on active capacity choice from front-end form
    if guest_capacity:
        if guest_capacity == "5":
            query += " WHERE max_adults >= %s"
            params.append(5)
        else:
            query += " WHERE max_adults >= %s"
            params.append(int(guest_capacity))
            
    query += " ORDER BY base_price ASC"

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        columns = [col[0] for col in cursor.description]
        room_types = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
    return render(request, 'bookings/index.html', {'room_types': room_types})


def about_view(request):
    """
    Renders the hotel info page publicly.
    """
    return render(request, 'bookings/about.html')


def contact_view(request):
    """
    Handles incoming visitor suggestions and inquiries from the frontend layout,
    storing the records securely into the database.
    """
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message_content = request.POST.get('message')

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO client_inquiries (name, email, message) VALUES (%s, %s, %s)",
                    [name, email, message_content]
                )
            messages.success(request, f"Thank you, {name}! Your luxury inquiry has been transmitted to our concierge desk.")
        except Exception as e:
            messages.error(request, f"An internal tracking error occurred: {e}")
            
        return redirect('contact')

    return render(request, 'bookings/contact.html')


# ==========================================
# 2. GATED VIEWS (Requires Registration/Login)
# ==========================================

@login_required(login_url='login')
def book_accommodation_view(request):
    """
    Gated Workspace. Fetches room specs on GET, and hooks up the reservation 
    to your custom 'bookings' table structure on POST, calculating the stay cost 
    and triggering a real-time Daraja API M-Pesa STK Push prompt.
    """
    selected_room_id = request.GET.get('room_id') or request.POST.get('room_id')
    
    if not selected_room_id:
        messages.error(request, "No room selection context provided. Please select a room first.")
        return redirect('home')

    # Fetch room pricing and specifications from the database
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, name, base_price, max_adults, status FROM room_types WHERE id = %s", [selected_room_id])
        row = cursor.fetchone()
        
        if not row:
            messages.error(request, "Selected room category does not exist.")
            return redirect('home')
            
        columns = [col[0] for col in cursor.description]
        room_data = dict(zip(columns, row))

    # Handle incoming reservation submissions (POST)
    if request.method == 'POST':
        guest_name = request.POST.get('guest_name')
        guest_phone = request.POST.get('guest_phone')
        check_in = request.POST.get('check_in')
        check_out = request.POST.get('check_out')
        
        # Calculate pricing calculations programmatically
        try:
            d1 = datetime.strptime(check_in, '%Y-%m-%d')
            d2 = datetime.strptime(check_out, '%Y-%m-%d')
            total_nights = (d2 - d1).days
            
            if total_nights <= 0:
                messages.error(request, "Checkout date must be later than the check-in date.")
                return redirect(f"{request.path}?room_id={selected_room_id}")
                
            total_price = float(room_data['base_price']) * total_nights
            
        except ValueError:
            messages.error(request, "Invalid date configurations supplied.")
            return redirect('home')

        try:
            with connection.cursor() as cursor:
                # 1. Insert details tracking cleanly as pending against your existing schema
                cursor.execute(
                    """
                    INSERT INTO bookings (guest_name, guest_phone, check_in, check_out, total_price, payment_status, room_type_id)
                    VALUES (%s, %s, %s, %s, %s, 'pending', %s) RETURNING id
                    """,
                    [guest_name, guest_phone, check_in, check_out, total_price, selected_room_id]
                )
                new_booking_id = cursor.fetchone()[0]
                
                # 2. Fire the M-Pesa STK push menu onto the handset screen automatically
                stk_response = initiate_stk_push(guest_phone, total_price, new_booking_id)
                
                if stk_response and stk_response.get("ResponseCode") == "0":
                    checkout_request_id = stk_response.get("CheckoutRequestID")
                    
                    cursor.execute(
                        "UPDATE bookings SET mpesa_checkout_id = %s WHERE id = %s",
                        [checkout_request_id, new_booking_id]
                    )
                    messages.success(request, f"STK Push prompt dispatched! Enter your PIN on phone {guest_phone} to clear KES {total_price}.")
                else:
                    messages.warning(request, "Room secured, but M-Pesa handshake failed. Please finalize payment at the front desk.")
                
                # Flip room status to let the dashboard know it's reserved
                cursor.execute("UPDATE room_types SET status = 'Occupied' WHERE id = %s", [selected_room_id])
                
            return redirect('home')
            
        except Exception as e:
            messages.error(request, f"Reservation processing system failed: {e}")
            return redirect('home')

    # Handle initial page presentation rendering (GET)
    # Pre-populates fields if they were filled out on the home filter bar
    context = {
        'room': room_data,
        'prefilled_checkin': request.GET.get('check_in', ''),
        'prefilled_checkout': request.GET.get('check_out', '')
    }
    return render(request, 'bookings/book_room.html', context)


# ==========================================
# 3. AUTHENTICATION CONTROLLERS (Supabase Auth Linking)
# ==========================================

def register_view(request):
    """
    Registers a guest user via Supabase Auth API.
    Pads the 4-digit pin to bypass Supabase's 6-character minimum requirement.
    """
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        raw_password = request.POST.get('password')

        secure_password = f"{raw_password}_padded_pin_auth"

        url = f"{SUPABASE_URL}/auth/v1/signup"
        headers = {
            "apikey": SUPABASE_ANON_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "email": email,
            "password": secure_password,
            "data": {"display_name": username}
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            response_data = response.json()

            if response.status_code == 200:
                if not User.objects.filter(username=email).exists():
                    User.objects.create_user(username=email, email=email, password=raw_password)
                
                messages.success(request, "Account created successfully! Please sign in.")
                return redirect('login')
            else:
                error_msg = response_data.get('msg', response_data.get('error_description', 'Registration failed.'))
                messages.error(request, f"Supabase Error: {error_msg}")
        
        except requests.exceptions.RequestException as e:
            messages.error(request, f"Connection error: {e}")

    return render(request, 'bookings/register.html')


def login_view(request):
    """
    Authenticates user credentials against Supabase Auth using the padded pin,
    then handles local Django framework session tracking.
    """
    if request.method == 'POST':
        email = request.POST.get('username')
        raw_password = request.POST.get('password')

        secure_password = f"{raw_password}_padded_pin_auth"

        url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
        headers = {
            "apikey": SUPABASE_ANON_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "email": email,
            "password": secure_password
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                try:
                    user = User.objects.get(username=email)
                    login(request, user)
                    return redirect('home')
                except User.DoesNotExist:
                    user = User.objects.create_user(username=email, email=email, password=raw_password)
                    login(request, user)
                    return redirect('home')
            else:
                messages.error(request, "Invalid email address or 4-digit pin combination.")
        
        except requests.exceptions.RequestException as e:
            messages.error(request, f"Connection error: {e}")

    return render(request, 'bookings/login.html')


def logout_view(request):
    """
    Clears local cookies and terminates user's session safely.
    """
    logout(request)
    messages.info(request, "Logged out successfully.")
    return redirect('home')


# ==========================================
# 4. ADMINISTRATIVE CONTROL PANELS (Staff Privileged)
# ==========================================

@login_required(login_url='login')
def admin_dashboard_view(request):
    """
    Gated Administrative Hub. Fetches global room configurations, active reservations,
    registered client data, and user inquiry messages from the database.
    """
    if not request.user.is_staff:
        messages.error(request, "Access denied. Premium administrative privileges required.")
        return redirect('home')

    with connection.cursor() as cursor:
        # 1. Fetch room parameters
        cursor.execute("SELECT id, name, base_price, max_adults, status FROM room_types")
        columns_rooms = [col[0] for col in cursor.description]
        rooms = [dict(zip(columns_rooms, row)) for row in cursor.fetchall()]

        # 2. Fetch the incoming customer inquiries/feedback
        cursor.execute("SELECT id, name, email, message, created_at FROM client_inquiries ORDER BY created_at DESC")
        columns_feedback = [col[0] for col in cursor.description]
        feedback_messages = [dict(zip(columns_feedback, row)) for row in cursor.fetchall()]

        # 3. Fetch live bookings with safe column fallbacks matching your template variable bindings
        cursor.execute(
            """
            SELECT id, guest_name, guest_phone AS mpesa_phone, check_in, check_out, 
                   total_price AS total_cost, (payment_status = 'confirmed') AS is_paid 
            FROM bookings 
            ORDER BY id DESC
            """
        )
        columns_bookings = [col[0] for col in cursor.description]
        active_bookings = [dict(zip(columns_bookings, row)) for row in cursor.fetchall()]

    total_users = User.objects.all().order_by('-date_joined')

    context = {
        'rooms': rooms,
        'feedback_messages': feedback_messages,
        'total_users': total_users,
        'active_bookings': active_bookings,
    }
    return render(request, 'bookings/admin_dashboard.html', context)


@login_required(login_url='login')
def update_room_status_view(request, room_id):
    """
    Allows authorized concierge staff to change room operational states.
    """
    if not request.user.is_staff:
        messages.error(request, "Privileged administrative credentials required.")
        return redirect('home')

    if request.method == 'POST':
        new_status = request.POST.get('status')

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE room_types SET status = %s WHERE id = %s",
                    [new_status, room_id]
                )
            messages.success(request, f"Status updated successfully to {new_status}.")
        except Exception as e:
            messages.error(request, f"Database modification failed: {e}")

    return redirect('admin_dashboard')


@login_required(login_url='login')
def resolve_enquiry_view(request, msg_id):
    """
    Allows authorized staff to mark incoming guest inquiries as resolved.
    """
    if not request.user.is_staff:
        messages.error(request, "Privileged administrative credentials required.")
        return redirect('home')
        
    try:
        with connection.cursor() as cursor:
            cursor.execute("UPDATE client_inquiries SET is_resolved = true WHERE id = %s", [msg_id])
        messages.success(request, "Enquiry successfully marked as addressed.")
    except Exception as e:
        messages.error(request, f"Could not update inquiry statement: {e}")
        
    return redirect('admin_dashboard')


# ==========================================
# 5. ASYNCHRONOUS WEBHOOKS (Safaricom Callback)
# ==========================================

@csrf_exempt
def mpesa_callback_view(request):
    """
    Headless Webhook Endpoint. Safaricom's validation engine POSTs transaction 
    results here asynchronously after a guest responds to the STK pin menu prompt.
    """
    if request.method == 'POST':
        try:
            callback_data = json.loads(request.body)
            stk_callback = callback_data.get('Body', {}).get('stkCallback', {})
            result_code = stk_callback.get('ResultCode')
            checkout_request_id = stk_callback.get('CheckoutRequestID')

            if result_code == 0:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE bookings SET payment_status = 'confirmed' WHERE mpesa_checkout_id = %s",
                        [checkout_request_id]
                    )
            else:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE bookings SET payment_status = 'failed' WHERE mpesa_checkout_id = %s",
                        [checkout_request_id]
                    )

            return JsonResponse({"ResultCode": 0, "ResultDesc": "Callback processed smoothly"}, status=200)
        
        except Exception as e:
            return JsonResponse({"ResultCode": 1, "ResultDesc": f"Webhook parsing anomaly: {e}"}, status=400)
            
    return JsonResponse({"Error": "Method not allowed"}, status=405)