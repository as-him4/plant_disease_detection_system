import os
import secrets

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from django.urls import reverse

from .models import UserProfile, ScanHistory, PasswordResetToken
from .ml_model.predictor import predict


# ─────────────────────────────────────────────
#  Authentication views
# ─────────────────────────────────────────────

def index(request):
    """Login / Register page. Redirect to home if already logged in."""
    if request.user.is_authenticated:
        return redirect('home')
    return render(request, 'index.html')


@require_POST
def login_view(request):
    """Handle login form submission via AJAX."""
    username_or_email = request.POST.get('emailOrUsername', '').strip()
    password          = request.POST.get('password', '')

    # Allow login with email OR username
    user = None
    if '@' in username_or_email:
        try:
            db_user = User.objects.get(email=username_or_email)
            user    = authenticate(request, username=db_user.username, password=password)
        except User.DoesNotExist:
            pass
    else:
        user = authenticate(request, username=username_or_email, password=password)

    if user is not None:
        login(request, user)
        return JsonResponse({'success': True, 'redirect': '/home/'})
    else:
        return JsonResponse({'success': False, 'error': 'Invalid credentials.'}, status=401)


@require_POST
def register_view(request):
    """Handle registration form submission via AJAX."""
    first_name       = request.POST.get('first_name', '').strip()
    last_name        = request.POST.get('last_name', '').strip()
    email            = request.POST.get('email', '').strip()
    phone_number     = request.POST.get('phoneNumber', '').strip()
    username         = request.POST.get('username', '').strip()
    password         = request.POST.get('password', '')
    confirm_password = request.POST.get('confirmpassword', '')

    # Validation
    if password != confirm_password:
        return JsonResponse({'success': False, 'error': 'Passwords do not match.'}, status=400)

    if len(password) < 8:
        return JsonResponse({'success': False, 'error': 'Password must be at least 8 characters.'}, status=400)

    if User.objects.filter(username=username).exists():
        return JsonResponse({'success': False, 'error': 'Username already taken.'}, status=400)

    if User.objects.filter(email=email).exists():
        return JsonResponse({'success': False, 'error': 'Email already registered.'}, status=400)

    # Create user
    user = User.objects.create_user(
        username   = username,
        email      = email,
        password   = password,
        first_name = first_name,
        last_name  = last_name,
    )

    # Create extended profile
    UserProfile.objects.create(user=user, phone_number=phone_number)

    return JsonResponse({'success': True, 'message': 'Registered successfully! Please login.'})


@login_required
def logout_view(request):
    """Log the user out and redirect to login page."""
    logout(request)
    return redirect('index')


# ─────────────────────────────────────────────
#  Main app views
# ─────────────────────────────────────────────

@login_required
def home(request):
    """Main home / upload page."""
    recent_scans = ScanHistory.objects.filter(user=request.user)[:5]
    context = {
        'user'        : request.user,
        'recent_scans': recent_scans,
    }
    return render(request, 'home.html', context)


@login_required
@require_POST
def analyze(request):
    """
    Receive uploaded image, save it, run ML model, return results as JSON.

    Returns:
        {
            "success"      : true,
            "disease_name" : "...",
            "confidence"   : "92.0%",
            "status"       : "completed" | "stub",
            "scan_id"      : 123
        }
    """
    image_file = request.FILES.get('image')

    # Validate image exists
    if not image_file:
        return JsonResponse({'success': False, 'error': 'No image provided.'}, status=400)

    # Validate file size (5MB max)
    if image_file.size > settings.MAX_UPLOAD_SIZE:
        return JsonResponse({'success': False, 'error': 'Image too large. Max size is 5MB.'}, status=400)

    # Validate file type
    allowed_types = ['image/jpeg', 'image/png', 'image/webp']
    if image_file.content_type not in allowed_types:
        return JsonResponse({'success': False, 'error': 'Only JPEG, PNG and WebP images are allowed.'}, status=400)

    # Save scan record as pending first
    scan = ScanHistory.objects.create(
        user   = request.user,
        image  = image_file,
        status = 'pending',
    )

    # Run prediction
    try:
        image_path = os.path.join(settings.MEDIA_ROOT, scan.image.name)
        result     = predict(image_path)

        scan.disease_name = result['disease_name']
        scan.confidence   = result['confidence']
        scan.raw_result   = result
        scan.status       = result.get('status', 'completed')
        scan.save()

        response_data = {
            'success'      : True,
            'disease_name' : scan.disease_name,
            'confidence'   : scan.confidence_percent(),
            'status'       : scan.status,
            'scan_id'      : scan.id,
        }

        # Add detailed leaf check metadata for debugging and frontend clarity
        if 'is_leaf' in result:
            response_data['is_leaf'] = result['is_leaf']
            response_data['leaf_label'] = result.get('leaf_label')
            response_data['leaf_confidence'] = result.get('leaf_confidence')

        return JsonResponse(response_data)

    except Exception as e:
        scan.status = 'failed'
        scan.save()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def scan_history(request):
    """Return the logged-in user's scan history as JSON."""
    scans = ScanHistory.objects.filter(user=request.user).values(
        'id', 'disease_name', 'confidence', 'status', 'created_at'
    )

    data = []
    for s in scans:
        data.append({
            'id'          : s['id'],
            'disease_name': s['disease_name'] or 'Pending',
            'confidence'  : f"{s['confidence'] * 100:.1f}%" if s['confidence'] else 'N/A',
            'status'      : s['status'],
            'created_at'  : s['created_at'].strftime('%Y-%m-%d %H:%M'),
        })

    return JsonResponse({'success': True, 'scans': data})


def password_reset_request(request):
    """Handle password reset request - user enters email."""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        
        if not email:
            return JsonResponse({'success': False, 'error': 'Please enter your email address.'}, status=400)
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return JsonResponse({'success': True, 'message': 'If an account exists with this email, you will receive a password reset link.'})
        
        reset_token = PasswordResetToken.generate_token(user)
        reset_link = request.build_absolute_uri(
            reverse('password_reset_confirm', kwargs={'token': reset_token.token})
        )
        
        subject = 'Password Reset Request - Plant Disease Detection'
        message = f'''
Hello {user.first_name or user.username},

You requested a password reset for your Plant Disease Detection account.

Click the link below to reset your password:
{reset_link}

This link will expire in 1 hour.

If you didn't request this, please ignore this email.

Best regards,
Plant Disease Detection Team
'''
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            return JsonResponse({'success': True, 'message': 'If an account exists with this email, you will receive a password reset link.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Failed to send email: {str(e)}'}, status=500)
    
    return render(request, 'password_reset_request.html')


def password_reset_confirm(request, token):
    """Validate token and show password reset form."""
    try:
        reset_token = PasswordResetToken.objects.get(token=token)
    except PasswordResetToken.DoesNotExist:
        return render(request, 'password_reset_confirm.html', {
            'error': 'Invalid or expired reset link. Please request a new one.'
        })
    
    if not reset_token.is_valid():
        return render(request, 'password_reset_confirm.html', {
            'error': 'This reset link has expired. Please request a new one.'
        })
    
    if request.method == 'POST':
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        
        if password != confirm_password:
            return JsonResponse({'success': False, 'error': 'Passwords do not match.'}, status=400)
        
        if len(password) < 8:
            return JsonResponse({'success': False, 'error': 'Password must be at least 8 characters.'}, status=400)
        
        reset_token.user.set_password(password)
        reset_token.user.save()
        reset_token.delete()
        
        return JsonResponse({'success': True, 'message': 'Password reset successfully! You can now login.'})
    
    return render(request, 'password_reset_confirm.html', {
        'token': token,
        'username': reset_token.user.username
    })