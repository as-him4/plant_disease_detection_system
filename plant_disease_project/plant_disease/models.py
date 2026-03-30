from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User
 
 
class UserProfile(models.Model):
    """Extended profile linked to Django's built-in User model."""
    user         = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    created_at   = models.DateTimeField(auto_now_add=True)
 
    def __str__(self):
        return f"{self.user.username}'s profile"
 
 
class ScanHistory(models.Model):
    """Stores every leaf image scan performed by a user."""

    STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('completed', 'Completed'),
        ('failed',    'Failed'),
    ]

    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name='scans')
    image        = models.ImageField(upload_to='scan_images/')
    disease_name = models.CharField(max_length=255, blank=True, null=True)
    confidence   = models.FloatField(blank=True, null=True)   # stored as 0.0 - 1.0
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at   = models.DateTimeField(auto_now_add=True)
    raw_result   = models.JSONField(blank=True, null=True)    # full model output saved here

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} — {self.disease_name or 'Pending'} ({self.created_at:%Y-%m-%d})"

    def confidence_percent(self):
        """Return confidence as a readable percentage string."""
        if self.confidence is not None:
            return f"{self.confidence * 100:.1f}%"
        return "N/A"


class PasswordResetToken(models.Model):
    """Token for password reset functionality."""

    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_tokens')
    token      = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Password reset token for {self.user.username}"

    def is_valid(self):
        """Check if token is still valid (not expired)."""
        from django.utils import timezone
        return timezone.now() < self.expires_at

    @classmethod
    def generate_token(cls, user):
        """Generate a new token for user, invalidating any existing ones."""
        import secrets
        from django.utils import timezone
        from datetime import timedelta

        cls.objects.filter(user=user).delete()

        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(hours=1)

        return cls.objects.create(
            user=user,
            token=token,
            expires_at=expires_at
        )