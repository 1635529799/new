from django.conf.urls import url
from . import views
from .views import *
urlpatterns = [

    url(r"^$", index, name="index"),
    url(r"^index$", index, name="index"),
    url(r"^rec$", rec, name="wenda"),
    url(r"^chat$", chat, name="wenda"),
    url(r"^get_all$", get_all_nodes, name="get_all"),
    url(r"^delete$", delete_relationship_view, name="delete"),
    url(r"^edit/$", edit, name="edit"),
    url(r"^add/$", add, name="add"),
    # url(r"^wenda$", wenda_html, name="wenda_html"),
    url(r"^upload$", upload_html, name="upload_html"),
    url(r"^progress$", views.get_progress, name="progress")


]
