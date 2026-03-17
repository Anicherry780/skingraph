import os
import resend
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/email")

# In a real app we would use resend.api_key = os.getenv("RESEND_API_KEY")
# But for Hackathon testing, we will use a dummy key or gracefully degraded response
RESEND_API_KEY = os.getenv("RESEND_API_KEY")

class DeletionEmailRequest(BaseModel):
    email: str

@router.post("/deletion-confirmation")
async def send_deletion_email(req: DeletionEmailRequest):
    """
    Sends an email to the user confirming their account was deleted.
    """
    if not req.email:
        raise HTTPException(status_code=400, detail="Email is required")
        
    if not RESEND_API_KEY:
        # Graceful degradation for local testing without an API key
        print(f"Mock Email sent to {req.email}: Your SkinGraph account was deleted.")
        return {"status": "success", "mock": True, "message": f"Simulated email bound for {req.email}"}

    try:
        resend.api_key = RESEND_API_KEY
        
        response = resend.Emails.send({
            "from": "SkinGraph Support <support@skingraph.com>", # Note: This requires a verified domain in Resend
            "to": [req.email],
            "subject": "Your SkinGraph Account Has Been Deleted",
            "html": f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #333;">
                    <h2 style="color: #ef4444;">Account Deleted Successfully</h2>
                    <p>Hello,</p>
                    <p>This email is to confirm that your SkinGraph account (<strong>{req.email}</strong>) and all associated data have been permanently deleted from our servers as requested.</p>
                    <p>This includes:</p>
                    <ul>
                        <li>Your skin profile and allergies</li>
                        <li>Your analysis history</li>
                        <li>Your saved and bookmarked products</li>
                    </ul>
                    <p>We're sorry to see you go! If you ever want to return, you can create a new account anytime at <a href="https://skin.anirudhdev.com">skin.anirudhdev.com</a>.</p>
                    <p>Best regards,<br>The SkinGraph Team</p>
                </div>
            """
        })
        return {"status": "success", "id": response["id"]}
    except Exception as e:
        # We don't want the frontend to crash the deletion if the email fails,
        # so we just print the error and return a warning
        print(f"Failed to send email: {str(e)}")
        return {"status": "warning", "message": "Email failed but deletion proceeded."}
