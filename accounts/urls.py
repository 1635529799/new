from django.conf.urls import url, include
from .views import *

urlpatterns = [
    url(r"^login$", user_login, name="login"),
    url(r"^logout$", user_logout, name="logout"),
    url(r"^register$", do_register, name="register"),
]