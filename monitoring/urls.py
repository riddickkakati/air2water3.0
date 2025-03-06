from django.urls import path, include
from . import views
from rest_framework import routers

router = routers.DefaultRouter()
router.register("groups", views.GroupViewset)
router.register("members", views.MemberViewset)
router.register("comments", views.CommentViewset)
router.register("users", views.UserViewSet)
router.register("profile", views.UserProfileViewset)
router.register("compute", views.MonitoringRunViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("authenticate/", views.CustomObtainAuthToken.as_view())
]
