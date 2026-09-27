"""
services/email_service.py
Email invitation integration supporting both Gmail SMTP (Option 1 - 100% Free to any recipient)
and Resend API.

Security:
- Never log or return sensitive credentials (SMTP passwords, API keys) in errors or API responses.
- All email dispatch occurs server-side only.
"""
from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, Optional

import resend

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending candidate assessment invitations via Gmail SMTP or Resend."""

    def __init__(self) -> None:
        self._settings = get_settings()

    def _mask_key(self, key: str) -> str:
        """Helper to sanitize sensitive keys/passwords from error messages."""
        if not key or len(key) <= 6:
            return "[REDACTED]"
        return f"{key[:3]}...{key[-3:]}"

    def send_assessment_invitation(
        self,
        *,
        to_email: str,
        candidate_name: str,
        job_title: str,
        assessment_url: str,
        expires_in_days: int = 7,
    ) -> Dict[str, Any]:
        """
        Send a candidate assessment invitation email using Gmail SMTP or Resend.

        Returns a dictionary:
            {"success": bool, "id": Optional[str], "error": Optional[str]}
        """
        subject = f"Invitation: Behavioral Assessment for {job_title}"

        # Clean HTML email
        html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{subject}</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0f172a; color: #f8fafc; margin: 0; padding: 32px 16px;">
  <div style="max-width: 580px; margin: 0 auto; background-color: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 32px; box-shadow: 0 10px 25px rgba(0,0,0,0.3);">
    
    <div style="margin-bottom: 24px;">
      <span style="display: inline-block; padding: 4px 12px; font-size: 12px; font-weight: 600; text-transform: uppercase; tracking: 0.05em; background-color: #3b82f6; color: #ffffff; border-radius: 9999px;">
        Assessment Invitation
      </span>
    </div>

    <h1 style="font-size: 22px; font-weight: 700; color: #ffffff; margin-top: 0; margin-bottom: 16px;">
      Behavioral Assessment: {job_title}
    </h1>

    <p style="font-size: 15px; line-height: 1.6; color: #cbd5e1; margin-bottom: 20px;">
      Hello <strong>{candidate_name}</strong>,
    </p>

    <p style="font-size: 15px; line-height: 1.6; color: #cbd5e1; margin-bottom: 20px;">
      You have been invited to complete a behavioral job-fit assessment for the <strong>{job_title}</strong> role.
      This assessment evaluates situational and behavioral competencies using the <strong>STAR method</strong> (Situation, Task, Action, Result).
    </p>

    <div style="background-color: #0f172a; border-left: 4px solid #3b82f6; border-radius: 6px; padding: 14px 18px; margin-bottom: 24px;">
      <p style="font-size: 13px; color: #94a3b8; margin: 0 0 6px 0;">Assessment Guidelines:</p>
      <ul style="font-size: 13px; color: #cbd5e1; margin: 0; padding-left: 20px;">
        <li>Structure responses with specific actions and measurable results</li>
        <li>Link expires in <strong>{expires_in_days} days</strong></li>
        <li>Ensure a stable connection before submitting</li>
      </ul>
    </div>

    <div style="text-align: center; margin: 32px 0;">
      <a href="{assessment_url}"
         style="background: linear-gradient(135deg, #2563eb, #1d4ed8); color: #ffffff; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 15px; display: inline-block; box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4);">
        Start Assessment &rarr;
      </a>
    </div>

    <p style="font-size: 12px; color: #64748b; line-height: 1.5; margin-top: 24px; word-break: break-all;">
      If the button above does not work, copy and paste this link into your browser:<br>
      <a href="{assessment_url}" style="color: #60a5fa;">{assessment_url}</a>
    </p>

    <hr style="border: none; border-top: 1px solid #334155; margin: 28px 0;" />

    <p style="font-size: 11px; color: #64748b; text-align: center; margin: 0;">
      AI-Assisted Behavioral Job-Fit Assessment &bull; Automated notification on behalf of the hiring team.
    </p>
  </div>
</body>
</html>
"""

        # Fallback text content
        text_content = f"""Hello {candidate_name},

You have been invited to complete a behavioral job-fit assessment for the {job_title} role.

Assessment link:
{assessment_url}

Please note:
- This link is unique to you and will expire in {expires_in_days} days.
- Use the STAR method (Situation, Task, Action, Result) for best results.

Good luck!
AI-Assisted Behavioral Job-Fit Assessment
"""

        provider = (self._settings.email_provider or "smtp").lower()
        smtp_user = self._settings.smtp_user.strip()
        smtp_pass = self._settings.smtp_password.strip()

        # Decide provider: use SMTP if configured or requested; fallback to Resend if configured
        if provider == "smtp" or (smtp_user and smtp_pass):
            return self._send_via_smtp(
                to_email=to_email,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
            )
        else:
            return self._send_via_resend(
                to_email=to_email,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
            )

    # ── SMTP Dispatch (Gmail / Standard TLS) ──────────────────────────────────

    def _send_via_smtp(
        self,
        *,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str,
    ) -> Dict[str, Any]:
        smtp_server = self._settings.smtp_server.strip() or "smtp.gmail.com"
        smtp_port = self._settings.smtp_port or 587
        smtp_user = self._settings.smtp_user.strip()
        smtp_password = self._settings.smtp_password.strip()

        if not smtp_user or not smtp_password or smtp_user == "your_gmail_address@gmail.com":
            logger.warning("SMTP credentials not configured. Email for %s skipped.", to_email)
            return {
                "success": False,
                "id": None,
                "error": "Gmail SMTP credentials not configured (set SMTP_USER and SMTP_PASSWORD in backend/.env).",
            }

        from_addr = self._settings.email_from.strip() or f"AI Job-Fit Assessment <{smtp_user}>"

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = to_email

        msg.attach(MIMEText(text_content, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        try:
            if smtp_port == 465:
                with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=12) as server:
                    server.login(smtp_user, smtp_password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(smtp_server, smtp_port, timeout=12) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_password)
                    server.send_message(msg)

            logger.info("Successfully sent SMTP email to %s via %s", to_email, smtp_server)
            return {"success": True, "id": "smtp_success", "error": None}
        except Exception as exc:
            raw_msg = str(exc)
            safe_msg = raw_msg.replace(smtp_password, "[REDACTED]") if smtp_password else raw_msg
            logger.error("Failed to send SMTP invitation to %s: %s", to_email, safe_msg)
            return {"success": False, "id": None, "error": safe_msg}

    # ── Resend Dispatch ───────────────────────────────────────────────────────

    def _send_via_resend(
        self,
        *,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str,
    ) -> Dict[str, Any]:
        api_key = self._settings.resend_api_key.strip()
        from_email = self._settings.email_from.strip()

        if not api_key or api_key == "your_resend_api_key_here":
            logger.warning("Resend API key not configured. Invitation for %s skipped.", to_email)
            return {
                "success": False,
                "id": None,
                "error": "Resend API key is not configured on the server.",
            }

        resend.api_key = api_key

        params = {
            "from": from_email,
            "to": [to_email],
            "subject": subject,
            "html": html_content,
            "text": text_content,
        }

        try:
            res = resend.Emails.send(params)
            email_id = None
            if isinstance(res, dict):
                email_id = res.get("id")
            elif hasattr(res, "id"):
                email_id = getattr(res, "id")
            elif hasattr(res, "get"):
                email_id = res.get("id")
            else:
                email_id = str(res)

            logger.info("Successfully sent Resend email to %s (id: %s)", to_email, email_id)
            return {"success": True, "id": email_id, "error": None}
        except Exception as exc:
            raw_msg = str(exc)
            safe_msg = raw_msg.replace(api_key, "[REDACTED]") if api_key else raw_msg
            logger.error("Failed to send Resend invitation to %s: %s", to_email, safe_msg)
            return {"success": False, "id": None, "error": safe_msg}
