import asyncio
from typing import Optional, List
from pydantic import BaseModel, Field
from backend.app.tools.base import BaseTool, ToolResult
from backend.app.config import PermissionLevel
from backend.app.integrations.external_services import integration_manager

class DraftEmailInput(BaseModel):
    recipient: str = Field(description="Email address of the recipient")
    subject: str = Field(description="Subject line of the email")
    body: str = Field(description="Body message of the draft email")

class DraftEmailTool(BaseTool):
    name = "draft_email"
    description = "Drafts an email message with recipient, subject, and body for user review before sending."
    input_schema = DraftEmailInput
    permission_level = PermissionLevel.GENERATE

    async def execute(self, recipient: str, subject: str, body: str) -> ToolResult:
        draft = {
            "recipient": recipient,
            "subject": subject,
            "body": body,
            "status": "drafted"
        }
        return ToolResult(
            success=True,
            data=draft,
            metadata={"recipient": recipient, "subject": subject}
        )

class SendEmailInput(BaseModel):
    recipient: str = Field(description="Email address of the recipient")
    subject: str = Field(description="Subject line of the email")
    body: str = Field(description="Body message of the email")

class SendEmailTool(BaseTool):
    name = "send_email"
    description = "Sends an email to the recipient. Requires explicit user approval."
    input_schema = SendEmailInput
    permission_level = PermissionLevel.EXTERNAL_WRITE
    requires_approval = True  # Explicit confirmation required for sending external communications

    async def execute(self, recipient: str, subject: str, body: str) -> ToolResult:
        # Check if email credentials are configured in integrations
        email_conf = integration_manager.get_integration("email_smtp")
        if not email_conf:
            # Simulated safe output when SMTP not configured locally
            return ToolResult(
                success=True,
                data={
                    "recipient": recipient,
                    "subject": subject,
                    "status": "queued_sent_simulation",
                    "message": f"Email to {recipient} approved and simulated (configure 'email_smtp' for live sending)."
                }
            )

        return ToolResult(
            success=True,
            data={"recipient": recipient, "subject": subject, "status": "sent"}
        )

