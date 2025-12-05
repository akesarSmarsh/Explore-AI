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
        entity_type = alert.get('entity_type', '')
        entity_value = alert.get('entity_value', '')
        
        severity_colors = {
            'low': '#22c55e',
            'medium': '#f59e0b', 
            'high': '#ef4444',
            'critical': '#dc2626'
        }
        severity_color = severity_colors.get(severity, '#6b7280')
        
        # Build anomaly rows with enhanced information
        anomaly_rows = ""
        for anomaly in anomalies[:10]:  # Limit to 10 anomalies
            timestamp = anomaly.get('timestamp', 'N/A')
            count = anomaly.get('count', 0)
            anomaly_type = anomaly.get('anomaly_type', 'unknown')
            baseline_value = anomaly.get('baseline_value', 0)
            trigger_reason = anomaly.get('trigger_reason', '')
            
            # Format anomaly type display
            type_colors = {
                'spike': '#ef4444',
                'silence': '#3b82f6',
                'unusual_pattern': '#f59e0b',
                'semantic_match': '#8b5cf6'  # Purple for semantic matches
            }
            type_color = type_colors.get(anomaly_type, '#6b7280')
            
            # Format type label
            type_labels = {
                'spike': 'Volume Spike',
                'silence': 'Silence',
                'unusual_pattern': 'Unusual Pattern',
                'semantic_match': 'Semantic Match'
            }
            type_label = type_labels.get(anomaly_type, anomaly_type)
            
            anomaly_rows += f"""
            <tr>
                <td style="padding: 12px; border-bottom: 1px solid #e5e7eb;">{timestamp}</td>
                <td style="padding: 12px; border-bottom: 1px solid #e5e7eb;">
                    <span style="background: {type_color}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">{type_label}</span>
                </td>
            </tr>
            """
            
            # Add trigger reason if available
            if trigger_reason:
                anomaly_rows += f"""
            <tr>
                <td colspan="2" style="padding: 8px 12px; border-bottom: 1px solid #e5e7eb; background: #f9fafb; font-size: 13px; color: #4b5563;">
                    <strong>Reason:</strong> {trigger_reason}
                </td>
            </tr>
                """
        
        # Build top entities section if available
        top_entities_html = ""
        if anomalies and anomalies[0].get('top_entities'):
            top_entities = anomalies[0].get('top_entities', [])
            if top_entities:
                entities_list = ""
                for ent in top_entities[:5]:
                    entity_text = ent.get('entity', 'Unknown')
                    entity_count = ent.get('count', 0)
                    entities_list += f"<li style='margin: 4px 0;'><strong>{entity_text}</strong> - {entity_count} mentions</li>"
                
                top_entities_html = f"""
                <div style="margin-top: 16px; padding: 12px; background: #f0f9ff; border-radius: 8px; border-left: 4px solid #3b82f6;">
                    <h4 style="margin: 0 0 8px 0; color: #1e40af;">Top Contributing Entities</h4>
                    <ul style="margin: 0; padding-left: 20px; color: #374151;">
                        {entities_list}
                    </ul>
                </div>
                """
        
        # Entity info section for entity_type alerts
        entity_info_html = ""
        if category == 'entity_type' and entity_type:
            entity_info_html = f"""
            <div style="margin-bottom: 16px; padding: 12px; background: #fef3c7; border-radius: 8px;">
                <strong>Entity Type:</strong> {entity_type}
                {f'<br><strong>Entity Value:</strong> {entity_value}' if entity_value else ''}
            </div>
            """
        
        # Smart AI info section
        smart_ai_info_html = ""
        if category == 'smart_ai':
            total_matches = sum(a.get('count', 0) for a in anomalies)
            smart_ai_info_html = f"""
            <div style="margin-bottom: 16px; padding: 12px; background: #f0e7fe; border-radius: 8px; border-left: 4px solid #8b5cf6;">
                <strong>🤖 Smart AI Semantic Search</strong><br>
                <span style="color: #6b7280;">Query: "{alert_desc[:100]}{'...' if len(alert_desc) > 100 else ''}"</span><br>
                <span style="color: #8b5cf6; font-weight: 600;">{total_matches} matching emails found across {len(anomalies)} time periods</span>
            </div>
            """
        
        # Dashboard URL
        dashboard_url = "http://localhost:5173/?tab=dashboard"
        
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
                    <p style="margin: 0 0 16px 0; color: #6b7280;">{alert_desc}</p>
                    
                    {entity_info_html}
                    {smart_ai_info_html}
                    
                    <!-- Anomalies Table -->
                    <h3 style="margin: 0 0 12px 0; color: #374151; font-size: 16px;">Detected Anomalies ({len(anomalies)})</h3>
                    <table style="width: 100%; border-collapse: collapse; background: #f9fafb; border-radius: 8px; overflow: hidden;">
                        <thead>
                            <tr style="background: #e5e7eb;">
                                <th style="padding: 12px; text-align: left; font-weight: 600; color: #374151;">Time</th>
                                <th style="padding: 12px; text-align: left; font-weight: 600; color: #374151;">Type</th>
                            </tr>
                        </thead>
                        <tbody>
                            {anomaly_rows}
                        </tbody>
                    </table>
                    
                    {f'<p style="margin-top: 8px; color: #9ca3af; font-size: 12px;">Showing 10 of {len(anomalies)} anomalies</p>' if len(anomalies) > 10 else ''}
                    
                    {top_entities_html}
                    
                    <!-- Action Button -->
                    <div style="margin-top: 24px; text-align: center;">
                        <a href="{dashboard_url}" style="display: inline-block; background: #3b82f6; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 600;">View in Dashboard</a>
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
        category = alert.get('category', 'unknown')
        entity_type = alert.get('entity_type', '')
        entity_value = alert.get('entity_value', '')
        
        text = f"""
ALERT TRIGGERED: {alert_name}
{'=' * 50}

Severity: {severity.upper()}
Category: {category.replace('_', ' ').title()}
Description: {alert_desc}
"""
        # Add entity info for entity_type alerts
        if category == 'entity_type' and entity_type:
            text += f"""\nEntity Type: {entity_type}"""
            if entity_value:
                text += f"\nEntity Value: {entity_value}"
            text += "\n"
        
        # Add Smart AI info
        if category == 'smart_ai':
            total_matches = sum(a.get('count', 0) for a in anomalies)
            text += f"""\n🤖 Smart AI Semantic Search
Query: "{alert_desc[:100]}{'...' if len(alert_desc) > 100 else ''}"
{total_matches} matching emails found across {len(anomalies)} time periods
"""
        
        text += f"""\nDetected Anomalies ({len(anomalies)}):
{'-' * 30}
"""
        for anomaly in anomalies[:10]:
            anomaly_type = anomaly.get('anomaly_type', 'unknown')
            trigger_reason = anomaly.get('trigger_reason', '')
            
            text += f"- {anomaly.get('timestamp', 'N/A')}\n"
            text += f"  Type: {anomaly_type}\n"
            if trigger_reason:
                text += f"  Reason: {trigger_reason}\n"
            text += "\n"
        
        # Add top entities if available
        if anomalies and anomalies[0].get('top_entities'):
            top_entities = anomalies[0].get('top_entities', [])
            if top_entities:
                text += f"\nTop Contributing Entities:\n{'-' * 30}\n"
                for ent in top_entities[:5]:
                    entity_text = ent.get('entity', 'Unknown')
                    entity_count = ent.get('count', 0)
                    text += f"  - {entity_text}: {entity_count} mentions\n"
        
        # Dashboard URL
        dashboard_url = "http://localhost:5173/?tab=dashboard"
        
        text += f"""
{'-' * 30}

View in Dashboard: {dashboard_url}

This is an automated alert from Email Intelligence System
Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return text


# Global instance
email_notification_service = EmailNotificationService()
