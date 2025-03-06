from django.urls import path, include
from . import views
from rest_framework import routers

router = routers.DefaultRouter()
router.register("groups", views.MLGroupViewset)
router.register("members", views.MLMemberViewset)
router.register("comments", views.MLCommentViewset)
router.register("users", views.UserViewSet)
router.register("profile", views.UserProfileViewset)
router.register("ml_analysis", views.MLRunViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("authenticate/", views.CustomObtainAuthToken.as_view())
]
