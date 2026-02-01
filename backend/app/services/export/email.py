"""
Email Export Service using SendGrid.
"""
import logging
from typing import Optional

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition

from app.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via SendGrid."""

    def __init__(self):
        self.api_key = settings.SENDGRID_API_KEY
        self.client = SendGridAPIClient(self.api_key) if self.api_key else None
        self.from_email = "noreply@scribber.app"

    def is_configured(self) -> bool:
        """Check if email service is properly configured."""
        return bool(self.api_key and self.client)

    async def send_transcription(
        self,
        to_email: str,
        project_title: str,
        transcription: str,
        summary: Optional[str] = None,
        include_attachment: bool = True,
    ) -> dict:
        """
        Send transcription and summary via email.

        Args:
            to_email: Recipient email address
            project_title: Title of the project
            transcription: Full transcription text
            summary: Optional summary text
            include_attachment: Whether to include a text file attachment

        Returns:
            dict with status and message
        """
        if not self.is_configured():
            return {
                "success": False,
                "message": "Email service not configured. Please set SENDGRID_API_KEY.",
            }

        try:
            # Build email content
            html_content = self._build_html_content(project_title, transcription, summary)
            plain_content = self._build_plain_content(project_title, transcription, summary)

            message = Mail(
                from_email=self.from_email,
                to_emails=to_email,
                subject=f"Scribber: {project_title}",
                html_content=html_content,
                plain_text_content=plain_content,
            )

            # Add attachment if requested
            if include_attachment:
                attachment_content = self._build_attachment_content(
                    project_title, transcription, summary
                )
                attachment = Attachment(
                    FileContent(attachment_content),
                    FileName(f"{project_title}.txt"),
                    FileType("text/plain"),
                    Disposition("attachment"),
                )
                message.attachment = attachment

            # Send email
            response = self.client.send(message)

            if response.status_code in [200, 202]:
                logger.info(f"Email sent successfully to {to_email}")
                return {
                    "success": True,
                    "message": f"Email sent to {to_email}",
                }
            else:
                logger.error(f"Email send failed: {response.status_code}")
                return {
                    "success": False,
                    "message": f"Failed to send email: {response.status_code}",
                }

        except Exception as e:
            logger.error(f"Email send error: {str(e)}")
            return {
                "success": False,
                "message": f"Email send failed: {str(e)}",
            }

    def _build_html_content(
        self,
        title: str,
        transcription: str,
        summary: Optional[str] = None,
    ) -> str:
        """Build HTML email content."""
        summary_section = ""
        if summary:
            summary_section = f"""
            <div style="margin-bottom: 24px;">
                <h2 style="color: #1e293b; font-size: 18px; margin-bottom: 12px;">Summary</h2>
                <div style="background: #f8fafc; padding: 16px; border-radius: 8px; white-space: pre-wrap;">
                    {summary}
                </div>
            </div>
            """

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #334155; max-width: 600px; margin: 0 auto; padding: 24px;">
            <div style="margin-bottom: 24px;">
                <h1 style="color: #6366f1; font-size: 24px; margin-bottom: 8px;">Scribber</h1>
                <p style="color: #64748b; margin: 0;">Audio Transcription & Summarization</p>
            </div>

            <div style="margin-bottom: 24px;">
                <h2 style="color: #1e293b; font-size: 20px; margin-bottom: 8px;">{title}</h2>
            </div>

            {summary_section}

            <div style="margin-bottom: 24px;">
                <h2 style="color: #1e293b; font-size: 18px; margin-bottom: 12px;">Full Transcription</h2>
                <div style="background: #f8fafc; padding: 16px; border-radius: 8px; white-space: pre-wrap; font-size: 14px;">
                    {transcription}
                </div>
            </div>

            <div style="margin-top: 32px; padding-top: 16px; border-top: 1px solid #e2e8f0; color: #94a3b8; font-size: 12px;">
                <p>Sent via Scribber - Audio Transcription & Summarization</p>
            </div>
        </body>
        </html>
        """

    def _build_plain_content(
        self,
        title: str,
        transcription: str,
        summary: Optional[str] = None,
    ) -> str:
        """Build plain text email content."""
        lines = [
            f"SCRIBBER - {title}",
            "=" * 50,
            "",
        ]

        if summary:
            lines.extend([
                "SUMMARY",
                "-" * 30,
                summary,
                "",
            ])

        lines.extend([
            "FULL TRANSCRIPTION",
            "-" * 30,
            transcription,
            "",
            "-" * 50,
            "Sent via Scribber - Audio Transcription & Summarization",
        ])

        return "\n".join(lines)

    def _build_attachment_content(
        self,
        title: str,
        transcription: str,
        summary: Optional[str] = None,
    ) -> str:
        """Build attachment content as base64."""
        import base64

        content = self._build_plain_content(title, transcription, summary)
        return base64.b64encode(content.encode()).decode()
