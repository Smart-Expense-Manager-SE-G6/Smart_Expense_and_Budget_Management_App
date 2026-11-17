from django.db import models


class EmailDeliveryFailure(models.Model):
    recipient = models.CharField(max_length=254, blank=True)
    subject = models.CharField(max_length=255, blank=True)
    reason = models.CharField(max_length=255)
    request_id = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Email delivery failure at {self.created_at}"
