"""
Notification service for sending alerts to drivers and riders.
Placeholder for push notifications, email, and SMS.
"""

import logging
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

from ..models import Driver, RideMatchOffer, PreBookedRide

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for handling all notifications"""
    
    def notify_driver_new_offer(self, driver: Driver, offer: RideMatchOffer):
        """Send notification to driver about new ride offer"""
        try:
            ride = offer.pre_booked_ride
            
            # Email notification
            subject = f"New ride offer - €{offer.total_fare}"
            
            context = {
                'driver_name': driver.user.get_full_name() or driver.user.username,
                'pickup_location': ride.pickup_location,
                'dropoff_location': ride.dropoff_location,
                'pickup_time': ride.pickup_datetime.strftime('%I:%M %p'),
                'pickup_date': ride.pickup_datetime.strftime('%B %d'),
                'fare': offer.total_fare,
                'distance': offer.distance_to_pickup_km,
                'expires_at': offer.expires_at.strftime('%I:%M %p'),
                'offer_id': offer.id,
                'special_requirements': ride.special_requirements,
                'wheelchair_required': ride.wheelchair_required,
            }
            
            # For now, use plain text email
            message = f"""
            New Ride Offer!
            
            Pickup: {context['pickup_location']}
            Dropoff: {context['dropoff_location']}
            Time: {context['pickup_time']} on {context['pickup_date']}
            Earnings: €{context['fare']}
            Distance to pickup: {context['distance']} km
            
            {'Wheelchair accessible vehicle required' if context['wheelchair_required'] else ''}
            {f"Special requirements: {context['special_requirements']}" if context['special_requirements'] else ''}
            
            This offer expires at {context['expires_at']}.
            
            Open your driver app to accept this ride.
            """
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [driver.user.email],
                fail_silently=True
            )
            
            # TODO: Implement push notification
            # self._send_push_notification(driver, subject, message)
            
            # TODO: Implement SMS notification
            # if driver.phone_number:
            #     self._send_sms(driver.phone_number, f"New ride: €{offer.total_fare} - Check app")
            
            logger.info(f"Sent new offer notification to driver {driver.id}")
            
        except Exception as e:
            logger.error(f"Error sending driver notification: {e}")
    
    def notify_rider_offer_accepted(self, booking: PreBookedRide):
        """Notify rider that their booking has been accepted"""
        try:
            rider = booking.rider
            driver = booking.matched_driver
            
            subject = "Your ride has been confirmed!"
            
            message = f"""
            Good news! Your ride has been confirmed.
            
            Driver: {driver.user.get_full_name() or driver.user.username}
            Vehicle: {booking.matched_vehicle.make} {booking.matched_vehicle.model}
            License Plate: {booking.matched_vehicle.license_plate}
            
            Pickup: {booking.pickup_location}
            Time: {booking.pickup_datetime.strftime('%I:%M %p on %B %d')}
            
            Your driver will arrive within your selected pickup window.
            
            Driver Rating: {driver.rating} ⭐
            
            You can track your ride in the app when it begins.
            """
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [rider.user.email],
                fail_silently=True
            )
            
            logger.info(f"Sent acceptance notification for booking {booking.id}")
            
        except Exception as e:
            logger.error(f"Error sending rider notification: {e}")
    
    def notify_driver_ride_reminder(self, booking: PreBookedRide):
        """Send reminder to driver about upcoming ride"""
        try:
            driver = booking.matched_driver
            hours_until = (booking.pickup_datetime - timezone.now()).total_seconds() / 3600
            
            subject = f"Ride reminder - {booking.pickup_datetime.strftime('%I:%M %p')}"
            
            message = f"""
            Reminder: You have a ride in {hours_until:.1f} hours
            
            Pickup: {booking.pickup_location}
            Dropoff: {booking.dropoff_location}
            Time: {booking.pickup_datetime.strftime('%I:%M %p')}
            
            Rider: {booking.rider.user.get_full_name() or booking.rider.user.username}
            {'Wheelchair user' if booking.wheelchair_required else ''}
            {f"Special requirements: {booking.special_requirements}" if booking.special_requirements else ''}
            
            Please ensure you arrive on time.
            """
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [driver.user.email],
                fail_silently=True
            )
            
        except Exception as e:
            logger.error(f"Error sending ride reminder: {e}")
    
    def notify_rider_driver_arriving(self, booking: PreBookedRide):
        """Notify rider that driver is arriving"""
        # TODO: Implement
        pass
    
    def _send_push_notification(self, user, title, body, data=None):
        """Send push notification (placeholder)"""
        # TODO: Integrate with FCM/APNs
        pass
    
    def _send_sms(self, phone_number, message):
        """Send SMS notification (placeholder)"""
        # TODO: Integrate with Twilio or similar
        pass