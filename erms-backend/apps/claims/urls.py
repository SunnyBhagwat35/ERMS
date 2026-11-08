from rest_framework.routers import DefaultRouter

from .views import ClaimViewSet, ExpenseCategoryViewSet

router = DefaultRouter()
router.register("claims", ClaimViewSet, basename="claim")
router.register("categories", ExpenseCategoryViewSet, basename="category")

urlpatterns = router.urls
