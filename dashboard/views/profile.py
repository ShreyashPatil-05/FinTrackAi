"""
Profile Management Views

User profile editing, avatar upload, and account deletion.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import logout as auth_logout
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.http import HttpRequest, HttpResponse

from ..models import UserProfile


@never_cache
@login_required(login_url='login')
def profile(request: HttpRequest) -> HttpResponse:
    """
    User profile management page.
    
    Features:
        - Update username, first name, last name, email
        - Upload/remove avatar (max 2MB, JPEG/PNG/GIF/WebP)
        - File type validation via magic bytes
        - Safe avatar deletion (works with local and S3 storage)
        
    Args:
        request: Django HttpRequest object
        
    Returns:
        HttpResponse: Profile page with success/error messages
    """
    user = request.user
    profile_obj, _ = UserProfile.objects.get_or_create(user=user)
    success = False

    if request.method == "POST":
        action = request.POST.get('action', 'profile')

        if action == 'avatar':
            if 'avatar' in request.FILES:
                avatar_file = request.FILES['avatar']

                if avatar_file.size > 2 * 1024 * 1024:
                    messages.error(request, 'Image too large. Maximum size is 2MB.')
                    return redirect('profile')

                header = avatar_file.read(12)
                avatar_file.seek(0)
                allowed_signatures = [
                    b'\xff\xd8\xff',
                    b'\x89PNG\r\n\x1a\n',
                    b'GIF87a', b'GIF89a',
                    b'RIFF',
                ]
                if not any(header.startswith(sig) for sig in allowed_signatures):
                    messages.error(request, 'Invalid file type. Only JPEG, PNG, GIF and WebP are allowed.')
                    return redirect('profile')

                # Delete old avatar safely (works for both local and S3)
                if profile_obj.avatar:
                    try:
                        profile_obj.avatar.delete(save=False)
                    except Exception:
                        pass
                profile_obj.avatar = avatar_file
                profile_obj.save(update_fields=['avatar'])
                success = True
        elif action == 'remove_avatar':
            if profile_obj.avatar:
                try:
                    profile_obj.avatar.delete(save=False)
                except Exception:
                    pass
                profile_obj.avatar = None
                profile_obj.save(update_fields=['avatar'])
                success = True
        else:
            new_username = request.POST.get("username", "").strip()
            if not new_username:
                messages.error(request, 'Username cannot be empty.')
                return redirect('profile')
            if User.objects.exclude(pk=user.pk).filter(username=new_username).exists():
                messages.error(request, f'Username "{new_username}" is already taken.')
                return redirect('profile')
            user.first_name = request.POST.get("first_name", "").strip()
            user.last_name  = request.POST.get("last_name", "").strip()
            user.username   = new_username
            user.email      = request.POST.get("email", "").strip()
            user.save()
            success = True

    return render(request, 'dashboard/profile.html', {
        'success': success,
        'profile_obj': profile_obj,
    })


@login_required(login_url='login')
def delete_account(request: HttpRequest) -> HttpResponse:
    """
    Delete user account with password confirmation.
    
    Security:
        - Requires password verification
        - Logs user out before deletion
        - Cascades to all related data
        
    Args:
        request: Django HttpRequest object
        
    Returns:
        HttpResponse: Redirect to landing page or profile
    """
    if request.method == 'POST':
        password = request.POST.get('confirm_password', '')
        if not request.user.check_password(password):
            messages.error(request, 'Incorrect password. Account not deleted.')
            return redirect('profile')
        user = request.user
        auth_logout(request)
        user.delete()
        messages.success(request, 'Your account has been deleted.')
        return redirect('landing')
    return redirect('profile')
