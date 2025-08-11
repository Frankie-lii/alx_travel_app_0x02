#!/usr/bin/env python3
import os
import requests
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Payment
from bookings.models import Booking  # update import path
from django.conf import settings

CHAPA_INITIATE_URL = "https://api.chapa.co/v1/transaction/initialize"  # verify in docs

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initiate_payment(request, booking_id):
    """
    Given a booking_id, initialize payment with Chapa and store Payment object.
    """
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    amount = booking.total_amount  # adjust field to your model
    # Create Payment record (Pending)
    payment, created = Payment.objects.get_or_create(
        booking=booking,
        defaults={'amount': amount, 'currency': 'ETB', 'status': 'PENDING'}
    )
    # If already has chapa_reference and checkout_url, return it
    if payment.checkout_url:
        return Response({
            'checkout_url': payment.checkout_url,
            'chapa_reference': payment.chapa_reference,
            'status': payment.status
        })

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}"
    }

    # transaction reference ideally unique (e.g., booking id + timestamp or uuid)
    import uuid
    tx_ref = f"booking_{booking.id}_{uuid.uuid4().hex[:8]}"

    payload = {
        "amount": str(amount),
        "currency": payment.currency,
        "first_name": request.user.first_name or '',
        "last_name": request.user.last_name or '',
        "email": request.user.email,
        "tx_ref": tx_ref,
        "return_url": request.build_absolute_uri(f"/payments/verify/?tx_ref={tx_ref}&booking_id={booking.id}")
    }

    resp = requests.post(CHAPA_INITIATE_URL, json=payload, headers=headers, timeout=15)
    if resp.status_code not in (200, 201):
        # update payment
        payment.status = 'FAILED'
        payment.save()
        return Response({"detail": "Failed to initiate payment", "raw": resp.text}, status=status.HTTP_400_BAD_REQUEST)

    data = resp.json()
    # typical response includes 'data' with checkout_url and reference — confirm with docs
    chapa_data = data.get('data', {})
    checkout_url = chapa_data.get('checkout_url') or chapa_data.get('checkout_url')
    chapa_reference = chapa_data.get('reference') or chapa_data.get('id') or tx_ref

    payment.chapa_reference = chapa_reference
    payment.checkout_url = checkout_url
    payment.save(update_fields=['chapa_reference', 'checkout_url', 'status', 'updated_at'])

    return Response({
        "checkout_url": checkout_url,
        "chapa_reference": chapa_reference,
        "status": payment.status
    })
