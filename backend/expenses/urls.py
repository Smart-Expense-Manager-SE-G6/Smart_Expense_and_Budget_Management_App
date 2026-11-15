from rest_framework.routers import DefaultRouter

from .views import CategoryViewSet, ExpenseViewSet, RecurringRuleViewSet

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("expenses", ExpenseViewSet, basename="expense")
router.register("recurring-rules", RecurringRuleViewSet, basename="recurring-rule")

urlpatterns = router.urls
