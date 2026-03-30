from django.urls import path
from . import views
 
urlpatterns = [
    # Auth
    path('',views.index,name='index'),
    path('login/',views.login_view,name='login'),
    path('register/',views.register_view,name='register'),
    path('logout/',views.logout_view,name='logout'),
    path('password-reset/',views.password_reset_request,name='password_reset_request'),
    path('password-reset/<str:token>/',views.password_reset_confirm,name='password_reset_confirm'),
 
    # Main app
    path('home/',views.home,name='home'),
    path('analyze/',views.analyze,name='analyze'),
    path('scan-history/',views.scan_history,name='scan_history'),
]