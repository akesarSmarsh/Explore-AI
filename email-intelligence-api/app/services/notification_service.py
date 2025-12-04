"""Notification Service for sending email alerts."""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional, List
from datetime import datetime
from string import Template
from sqlalchemy.orm import Session

from app.config import settings
from app.models import SmartAlert, AlertHistory, EmailNotification


class NotificationService:
    """Service for sending email notifications."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def send_alert_notification(
        self,
        alert: SmartAlert,
        history: AlertHistory,
        matched_data: Dict[str, Any]
    ) -> bool:
        """
        Send notification for a triggered alert.
        
        Args:
            alert: The smart alert that was triggered
            history: The alert history record
            matched_data: The data that matched the alert
            
        Returns:
            True if notification was sent successfully
        """
        notifications_config = alert.notifications or {}
        email_config = notifications_config.get("email", {})
        
        if not email_config.get("enabled", False):
            return False
        
        recipients = email_config.get("recipients", [])
        if not recipients:
            return False
        
        # Generate email content
        subject = self._render_template(
            email_config.get("subject_template", "Alert: {{alert_name}} triggered"),
            alert=alert,
            history=history,
            matched_data=matched_data
        )
        
        body = self._render_template(
            email_config.get("body_template") or self._get_default_body_template(),
            alert=alert,
            history=history,
            matched_data=matched_data
        )
        
        # Send to each recipient
        success = True
        for recipient in recipients:
            notification = EmailNotification(
                alert_history_id=history.id,
                recipient=recipient,
                subject=subject,
                body=body,
                status="pending"
            )
            self.db.add(notification)
            self.db.flush()
            
            try:
                self._send_email(recipient, subject, body)
                notification.status = "sent"
                notification.sent_at = datetime.utcnow()
            except Exception as e:
                notification.status = "failed"
                notification.error_message = str(e)
                success = False
        
        # Update history
        history.notification_sent = success
        history.notification_status = "sent" if success else "failed"
        
        self.db.commit()
        return success
    
    def _send_email(self, to: str, subject: str, body: str):
        """
        Send an email using SMTP.
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body (HTML)
        """
        # Get SMTP configuration
        smtp_host = getattr(settings, 'smtp_host', None)
        smtp_port = getattr(settings, 'smtp_port', 587)
        smtp_user = getattr(settings, 'smtp_user', None)
        smtp_password = getattr(settings, 'smtp_password', None)
        smtp_from = getattr(settings, 'smtp_from', smtp_user)
        
        if not smtp_host or not smtp_user:
            raise ValueError("SMTP not configured. Set SMTP_HOST, SMTP_USER, SMTP_PASSWORD in environment.")
        
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = smtp_from
        msg["To"] = to
        
        # Add HTML body
        html_part = MIMEText(body, "html")
        msg.attach(html_part)
        
        # Send via SMTP
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_from, to, msg.as_string())
    
    def _render_template(
        self,
        template_str: str,
        alert: SmartAlert,
        history: AlertHistory,
        matched_data: Dict[str, Any]
    ) -> str:
        """Render a template string with alert data."""
        # Build context
        context = {
            "alert_name": alert.name,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "triggered_at": history.triggered_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "summary": history.summary or "",
            "match_count": matched_data.get("total_matches", 0),
        }
        
        # Add anomaly-specific data
        if alert.alert_type == "volume_spike":
            context["current_count"] = matched_data.get("current_count", 0)
            context["baseline_avg"] = matched_data.get("baseline_avg", 0)
            context["entity_type"] = matched_data.get("entity_type", "")
        
        # Simple template replacement using {{variable}}
        result = template_str
        for key, value in context.items():
            result = result.replace("{{" + key + "}}", str(value))
        
        return result
    
    def _get_default_body_template(self) -> str:
        """Get default email body template."""
        return """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #2563eb; color: white; padding: 20px; border-radius: 8px 8px 0 0; }
        .content { background: #f8fafc; padding: 20px; border: 1px solid #e2e8f0; }
        .severity-high { color: #dc2626; }
        .severity-critical { color: #991b1b; font-weight: bold; }
        .severity-medium { color: #d97706; }
        .severity-low { color: #059669; }
        .footer { background: #f1f5f9; padding: 15px; text-align: center; font-size: 12px; color: #64748b; border-radius: 0 0 8px 8px; }
        .stats { display: flex; gap: 20px; margin: 15px 0; }
        .stat-box { background: white; padding: 15px; border-radius: 8px; flex: 1; text-align: center; border: 1px solid #e2e8f0; }
        .stat-value { font-size: 24px; font-weight: bold; color: #2563eb; }
        .stat-label { font-size: 12px; color: #64748b; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2 style="margin: 0;">🚨 Alert Triggered: {{alert_name}}</h2>
        </div>
        <div class="content">
            <p><strong>Alert Type:</strong> {{alert_type}}</p>
            <p><strong>Severity:</strong> <span class="severity-{{severity}}">{{severity}}</span></p>
            <p><strong>Triggered At:</strong> {{triggered_at}}</p>
            
            <h3>Summary</h3>
            <p>{{summary}}</p>
            
            <div class="stats">
                <div class="stat-box">
                    <div class="stat-value">{{match_count}}</div>
                    <div class="stat-label">Matches Found</div>
                </div>
            </div>
            
            <p style="margin-top: 20px;">
                <a href="#" style="background: #2563eb; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                    View in Dashboard
                </a>
            </p>
        </div>
        <div class="footer">
            Email Intelligence API - Automated Alert Notification
        </div>
    </div>
</body>
</html>
"""
    
    def get_notification_status(self, history_id: str) -> List[Dict[str, Any]]:
        """Get notification status for an alert history entry."""
        notifications = self.db.query(EmailNotification).filter(
            EmailNotification.alert_history_id == history_id
        ).all()
        
        return [
            {
                "id": n.id,
                "recipient": n.recipient,
                "status": n.status,
                "sent_at": n.sent_at,
                "error_message": n.error_message
            }
            for n in notifications
        ]
    
    def retry_failed_notifications(self, history_id: str) -> int:
        """Retry failed notifications for an alert history entry."""
        notifications = self.db.query(EmailNotification).filter(
            EmailNotification.alert_history_id == history_id,
            EmailNotification.status == "failed"
        ).all()
        
        retried = 0
        for notification in notifications:
            try:
                self._send_email(
                    notification.recipient,
                    notification.subject,
                    notification.body
                )
                notification.status = "sent"
                notification.sent_at = datetime.utcnow()
                notification.error_message = None
                retried += 1
            except Exception as e:
                notification.error_message = str(e)
        
        self.db.commit()
        return retried










