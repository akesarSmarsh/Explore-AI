"""Email notification service for sending alert notifications."""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Dict, Any, Optional

from app.config import settings

logger = logging.getLogger(__name__)


class EmailNotificationService:
    """Service for sending email notifications."""
    
    def __init__(self):
        self.host = settings.smtp_host
        self.port = settings.smtp_port
        self.user = settings.smtp_user
        self.password = settings.smtp_password
        self.from_addr = settings.smtp_from
        self.use_tls = settings.smtp_use_tls
        self.use_ssl = settings.smtp_use_ssl
    
    def send_email(
        self,
        to_addresses: List[str],
        subject: str,
        html_body: str,
        text_body: Optional[str] = None
    ) -> bool:
        """
        Send an email notification.
        
        Args:
            to_addresses: List of recipient email addresses
            subject: Email subject
            html_body: HTML content of the email
            text_body: Plain text fallback (optional)
            
        Returns:
            True if email sent successfully, False otherwise
        """
        print(f"[EMAIL] Attempting to send email to {to_addresses}")
        print(f"[EMAIL] SMTP config: host={self.host}, port={self.port}, from={self.from_addr}")
        print(f"[EMAIL] smtp_configured={settings.smtp_configured}")
        
        if not settings.smtp_configured:
            logger.warning("SMTP not configured, skipping email notification")
            print("[EMAIL] ERROR: SMTP not configured!")
            return False
        
        if not to_addresses:
            logger.warning("No recipients specified")
            print("[EMAIL] ERROR: No recipients!")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_addr
            msg['To'] = ', '.join(to_addresses)
            
            # Add plain text part
            if text_body:
                part1 = MIMEText(text_body, 'plain')
                msg.attach(part1)
            
            # Add HTML part
            part2 = MIMEText(html_body, 'html')
            msg.attach(part2)
            
            print(f"[EMAIL] Connecting to {self.host}:{self.port}...")
            
            # Connect and send
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.host, self.port)
            else:
                server = smtplib.SMTP(self.host, self.port)
            
            if self.use_tls:
                server.starttls()
            
            if self.user and self.password:
                server.login(self.user, self.password)
            
            server.sendmail(self.from_addr, to_addresses, msg.as_string())
            server.quit()
            
            logger.info(f"Email sent successfully to {to_addresses}")
            print(f"[EMAIL] SUCCESS! Email sent to {to_addresses}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            print(f"[EMAIL] FAILED: {e}")
            return False
    
    def send_alert_notification(
        self,
        alert: Dict[str, Any],
        anomalies: List[Dict[str, Any]],
        recipients: Optional[List[str]] = None
    ) -> bool:
        """
        Send an alert notification email.
        
        Args:
            alert: The alert configuration
            anomalies: List of detected anomalies
            recipients: Override recipients (uses config if not provided)
        """
        print(f"[ALERT EMAIL] Sending notification for alert: {alert.get('name')}")
        print(f"[ALERT EMAIL] Anomalies count: {len(anomalies)}")
        
        if not recipients:
            recipients = settings.alert_recipients_list
            print(f"[ALERT EMAIL] Using config recipients: {recipients}")
        
        if not recipients:
            logger.warning("No alert recipients configured")
            print("[ALERT EMAIL] ERROR: No recipients configured!")
            return False
        
        # Build email content
        subject = f"🚨 Alert Triggered: {alert.get('name', 'Unknown Alert')}"
        
        html_body = self._build_alert_html(alert, anomalies)
        text_body = self._build_alert_text(alert, anomalies)
        
        print(f"[ALERT EMAIL] Sending to {recipients} with subject: {subject}")
        return self.send_email(recipients, subject, html_body, text_body)
    
    def _build_alert_html(self, alert: Dict[str, Any], anomalies: List[Dict[str, Any]]) -> str:
        """Build HTML email body for alert notification."""
        alert_name = alert.get('name', 'Unknown Alert')
        alert_desc = alert.get('description', '')
        category = alert.get('category', 'unknown')
        severity = alert.get('severity', 'medium')
        
        severity_colors = {
            'low': '#22c55e',
            'medium': '#f59e0b', 
            'high': '#ef4444',
            'critical': '#dc2626'
        }
        severity_color = severity_colors.get(severity, '#6b7280')
        
        # Build anomaly rows
        anomaly_rows = ""
        for anomaly in anomalies[:10]:  # Limit to 10 anomalies
            timestamp = anomaly.get('timestamp', 'N/A')
            count = anomaly.get('count', 0)
            anomaly_type = anomaly.get('anomaly_type', 'unknown')
            
            anomaly_rows += f"""
            <tr>
                <td style="padding: 12px; border-bottom: 1px solid #e5e7eb;">{timestamp}</td>
                <td style="padding: 12px; border-bottom: 1px solid #e5e7eb;">{count}</td>
                <td style="padding: 12px; border-bottom: 1px solid #e5e7eb;">{anomaly_type}</td>
            </tr>
            """
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background-color: #f3f4f6;">
            <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <!-- Header -->
                <div style="background: linear-gradient(135deg, #3b82f6, #8b5cf6); padding: 24px; color: white;">
                    <h1 style="margin: 0; font-size: 24px;">🚨 Alert Triggered</h1>
                    <p style="margin: 8px 0 0 0; opacity: 0.9;">Email Intelligence System</p>
                </div>
                
                <!-- Alert Info -->
                <div style="padding: 24px;">
                    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px;">
                        <span style="background: {severity_color}; color: white; padding: 4px 12px; border-radius: 9999px; font-size: 12px; font-weight: 600; text-transform: uppercase;">{severity}</span>
                        <span style="background: #e5e7eb; padding: 4px 12px; border-radius: 9999px; font-size: 12px; color: #4b5563;">{category.replace('_', ' ').title()}</span>
                    </div>
                    
                    <h2 style="margin: 0 0 8px 0; color: #1f2937;">{alert_name}</h2>
                    <p style="margin: 0 0 24px 0; color: #6b7280;">{alert_desc}</p>
                    
                    <!-- Anomalies Table -->
                    <h3 style="margin: 0 0 12px 0; color: #374151; font-size: 16px;">Detected Anomalies ({len(anomalies)})</h3>
                    <table style="width: 100%; border-collapse: collapse; background: #f9fafb; border-radius: 8px; overflow: hidden;">
                        <thead>
                            <tr style="background: #e5e7eb;">
                                <th style="padding: 12px; text-align: left; font-weight: 600; color: #374151;">Time</th>
                                <th style="padding: 12px; text-align: left; font-weight: 600; color: #374151;">Count</th>
                                <th style="padding: 12px; text-align: left; font-weight: 600; color: #374151;">Type</th>
                            </tr>
                        </thead>
                        <tbody>
                            {anomaly_rows}
                        </tbody>
                    </table>
                    
                    {f'<p style="margin-top: 8px; color: #9ca3af; font-size: 12px;">Showing 10 of {len(anomalies)} anomalies</p>' if len(anomalies) > 10 else ''}
                    
                    <!-- Action Button -->
                    <div style="margin-top: 24px; text-align: center;">
                        <a href="http://localhost:5173/?tab=dashboard" style="display: inline-block; background: #3b82f6; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 600;">View in Dashboard</a>
                    </div>
                </div>
                
                <!-- Footer -->
                <div style="background: #f9fafb; padding: 16px 24px; border-top: 1px solid #e5e7eb;">
                    <p style="margin: 0; color: #9ca3af; font-size: 12px; text-align: center;">
                        This is an automated alert from Email Intelligence System<br>
                        Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        return html
    
    def _build_alert_text(self, alert: Dict[str, Any], anomalies: List[Dict[str, Any]]) -> str:
        """Build plain text email body for alert notification."""
        alert_name = alert.get('name', 'Unknown Alert')
        alert_desc = alert.get('description', '')
        severity = alert.get('severity', 'medium')
        
        text = f"""
ALERT TRIGGERED: {alert_name}
{'=' * 50}

Severity: {severity.upper()}
Description: {alert_desc}

Detected Anomalies ({len(anomalies)}):
{'-' * 30}
"""
        for anomaly in anomalies[:10]:
            text += f"- {anomaly.get('timestamp', 'N/A')}: Count={anomaly.get('count', 0)}, Type={anomaly.get('anomaly_type', 'unknown')}\n"
        
        text += f"""
{'-' * 30}

View in Dashboard: http://localhost:5173/?tab=dashboard

This is an automated alert from Email Intelligence System
Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return text


# Global instance
email_notification_service = EmailNotificationService()
