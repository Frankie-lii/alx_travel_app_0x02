#!/usr/bin/env python3
from django.db import models
from django.conf import settings

class Payment(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    ]

    booking = models.OneToOneField(
        'bookings.Booking',  # or the actual Booking model path
        on_delete=models.CASCADE,
        related_name='payment'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='ETB')  # or 'KES' depending on Chapa account
    chapa_reference = models.CharField(max_length=255, blank=True, null=True)
    checkout_url = models.URLField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def mark_completed(self):
        self.status = 'COMPLETED'
        self.save(update_fields=['status', 'updated_at'])

    def mark_failed(self):
        self.status = 'FAILED'
        self.save(update_fields=['status', 'updated_at'])

    def __str__(self):
        return f'Payment {self.id} for Booking {self.booking_id} - {self.status}'
