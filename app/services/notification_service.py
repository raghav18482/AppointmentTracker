from typing import Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
import logging

from app.models.notification import Notification, NotificationStatus, NotificationType
from app.models.queue import QueueItem
from app.models.customer import Customer
from app.core.config import settings

logger = logging.getLogger(__name__)


class WhatsAppProvider:
    """WhatsApp provider interface - ready for Twilio/Gupshup integration."""
    
    def __init__(self):
        # Load from settings
        self.twilio_account_sid = settings.TWILIO_ACCOUNT_SID or ""
        self.twilio_auth_token = settings.TWILIO_AUTH_TOKEN or ""
        self.twilio_whatsapp_from = settings.TWILIO_WHATSAPP_FROM or ""
        
        self.gupshup_api_key = settings.GUPSHUP_API_KEY or ""
        self.gupshup_app_name = settings.GUPSHUP_APP_NAME or ""
        self.provider = settings.WHATSAPP_PROVIDER  # twilio or gupshup
    
    def send_whatsapp(
        self,
        to_phone: str,
        message: str,
        template_name: Optional[str] = None
    ) -> dict:
        """
        Send WhatsApp message using Twilio or Gupshup.
        This is a stub implementation - replace with actual API calls.
        
        Args:
            to_phone: Recipient phone number (E.164 format)
            message: Message body
            template_name: Optional template name for template messages
        
        Returns:
            Dictionary with 'success', 'message_id', and optional 'error'
        """
        try:
            if self.provider == "twilio":
                return self._send_via_twilio(to_phone, message, template_name)
            elif self.provider == "gupshup":
                return self._send_via_gupshup(to_phone, message, template_name)
            else:
                logger.warning(f"Unknown WhatsApp provider: {self.provider}")
                # Stub: simulate success for development
                return {
                    "success": True,
                    "message_id": f"stub_{datetime.utcnow().timestamp()}",
                    "error": None
                }
        except Exception as e:
            logger.error(f"Error sending WhatsApp: {e}")
            return {
                "success": False,
                "message_id": None,
                "error": str(e)
            }
    
    def _send_via_twilio(
        self,
        to_phone: str,
        message: str,
        template_name: Optional[str] = None
    ) -> dict:
        """
        Send WhatsApp via Twilio API.
        TODO: Implement actual Twilio API call.
        
        Example implementation:
        from twilio.rest import Client
        
        client = Client(self.twilio_account_sid, self.twilio_auth_token)
        message = client.messages.create(
            from_=f'whatsapp:{self.twilio_whatsapp_from}',
            body=message,
            to=f'whatsapp:{to_phone}'
        )
        return {
            "success": True,
            "message_id": message.sid,
            "error": None
        }
        """
        # Stub implementation
        logger.info(f"[TWILIO STUB] Sending WhatsApp to {to_phone}: {message[:50]}...")
        return {
            "success": True,
            "message_id": f"twilio_{datetime.utcnow().timestamp()}",
            "error": None
        }
    
    def _send_via_gupshup(
        self,
        to_phone: str,
        message: str,
        template_name: Optional[str] = None
    ) -> dict:
        """
        Send WhatsApp via Gupshup API.
        TODO: Implement actual Gupshup API call.
        
        Example implementation:
        import requests
        
        url = "https://api.gupshup.io/sm/api/v1/msg"
        headers = {
            "apikey": self.gupshup_api_key,
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "channel": "whatsapp",
            "source": self.gupshup_app_name,
            "destination": to_phone,
            "message": message
        }
        response = requests.post(url, headers=headers, data=data)
        return {
            "success": response.status_code == 200,
            "message_id": response.json().get("messageId"),
            "error": None if response.status_code == 200 else response.text
        }
        """
        # Stub implementation
        logger.info(f"[GUPSHUP STUB] Sending WhatsApp to {to_phone}: {message[:50]}...")
        return {
            "success": True,
            "message_id": f"gupshup_{datetime.utcnow().timestamp()}",
            "error": None
        }


class NotificationService:
    """Service for managing notifications with retry logic."""
    
    def __init__(self, db: Session):
        self.db = db
        self.whatsapp_provider = WhatsAppProvider()
    
    def send_queue_notification(
        self,
        queue_item_id: UUID,
        message_template: Optional[str] = None,
        custom_message: Optional[str] = None
    ) -> Optional[Notification]:
        """
        Send notification for a queue item.
        
        Args:
            queue_item_id: Queue item ID
            message_template: Optional template name
            custom_message: Optional custom message (overrides template)
        
        Returns:
            Created Notification object
        """
        # Get queue item with customer
        queue_item = self.db.query(QueueItem).filter(
            QueueItem.id == queue_item_id
        ).first()
        
        if not queue_item:
            logger.error(f"Queue item {queue_item_id} not found")
            return None
        
        customer = queue_item.customer
        
        # Check if WhatsApp is enabled
        if not customer.whatsapp_enabled:
            logger.warning(f"WhatsApp not enabled for customer {customer.id}")
            return None
        
        # Generate message
        if custom_message:
            message = custom_message
        elif message_template:
            message = self._get_template_message(message_template, queue_item, customer)
        else:
            message = self._get_default_message(queue_item, customer)
        
        # Create notification record
        notification = Notification(
            queue_item_id=queue_item_id,
            customer_id=customer.id,
            business_id=queue_item.business_id,
            notification_type=NotificationType.WHATSAPP.value,
            recipient_phone=customer.phone,
            recipient_email=customer.email,
            message_template=message_template,
            message_body=message,
            status=NotificationStatus.PENDING,
            retry_count=0,
            max_retries=3
        )
        
        self.db.add(notification)
        self.db.flush()
        
        # Send notification
        success = self._send_notification(notification)
        
        if success:
            notification.status = NotificationStatus.SENT
            notification.sent_at = datetime.utcnow()
        else:
            notification.status = NotificationStatus.FAILED
        
        self.db.commit()
        self.db.refresh(notification)
        
        return notification
    
    def _send_notification(self, notification: Notification) -> bool:
        """
        Send notification via WhatsApp provider.
        
        Args:
            notification: Notification object
        
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            result = self.whatsapp_provider.send_whatsapp(
                to_phone=notification.recipient_phone,
                message=notification.message_body,
                template_name=notification.message_template
            )
            
            if result["success"]:
                notification.external_id = result["message_id"]
                notification.error_message = None
                return True
            else:
                notification.error_message = result.get("error", "Unknown error")
                return False
                
        except Exception as e:
            logger.error(f"Error sending notification {notification.id}: {e}")
            notification.error_message = str(e)
            return False
    
    def retry_failed_notification(
        self,
        notification_id: UUID
    ) -> Optional[Notification]:
        """
        Retry a failed notification.
        
        Args:
            notification_id: Notification ID
        
        Returns:
            Updated Notification object, or None if max retries reached
        """
        notification = self.db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.status == NotificationStatus.FAILED
        ).first()
        
        if not notification:
            return None
        
        # Check if max retries reached
        if notification.retry_count >= notification.max_retries:
            logger.warning(f"Max retries reached for notification {notification_id}")
            return notification
        
        # Increment retry count
        notification.retry_count += 1
        notification.status = NotificationStatus.PENDING
        notification.error_message = None
        
        self.db.flush()
        
        # Retry sending
        success = self._send_notification(notification)
        
        if success:
            notification.status = NotificationStatus.SENT
            notification.sent_at = datetime.utcnow()
        else:
            notification.status = NotificationStatus.FAILED
        
        self.db.commit()
        self.db.refresh(notification)
        
        return notification
    
    def retry_all_failed_notifications(
        self,
        business_id: Optional[UUID] = None
    ) -> int:
        """
        Retry all failed notifications (background job).
        
        Args:
            business_id: Optional business ID to filter by
        
        Returns:
            Number of notifications retried
        """
        query = self.db.query(Notification).filter(
            Notification.status == NotificationStatus.FAILED,
            Notification.retry_count < Notification.max_retries
        )
        
        if business_id:
            query = query.filter(Notification.business_id == business_id)
        
        failed_notifications = query.all()
        retried_count = 0
        
        for notification in failed_notifications:
            try:
                result = self.retry_failed_notification(notification.id)
                if result and result.status == NotificationStatus.SENT:
                    retried_count += 1
            except Exception as e:
                logger.error(f"Error retrying notification {notification.id}: {e}")
        
        return retried_count
    
    def _get_default_message(self, queue_item: QueueItem, customer: Customer) -> str:
        """Generate default notification message."""
        return (
            f"Hello {customer.firstname},\n\n"
            f"Your queue position is {queue_item.position}.\n"
            f"Please be ready for your turn.\n\n"
            f"Thank you!"
        )
    
    def _get_template_message(
        self,
        template_name: str,
        queue_item: QueueItem,
        customer: Customer
    ) -> str:
        """
        Get message from template.
        TODO: Implement template system.
        """
        # Stub: return default message for now
        return self._get_default_message(queue_item, customer)
    
    def update_notification_status(
        self,
        external_id: str,
        status: NotificationStatus,
        error_message: Optional[str] = None
    ) -> Optional[Notification]:
        """
        Update notification status from webhook (delivered, read, etc.).
        
        Args:
            external_id: External message ID from provider
            status: New status
            error_message: Optional error message
        
        Returns:
            Updated Notification object
        """
        notification = self.db.query(Notification).filter(
            Notification.external_id == external_id
        ).first()
        
        if not notification:
            return None
        
        notification.status = status
        
        if status == NotificationStatus.DELIVERED:
            notification.delivered_at = datetime.utcnow()
        elif status == NotificationStatus.READ:
            notification.read_at = datetime.utcnow()
        
        if error_message:
            notification.error_message = error_message
        
        self.db.commit()
        self.db.refresh(notification)
        
        return notification

