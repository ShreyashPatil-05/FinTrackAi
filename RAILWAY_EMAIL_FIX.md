# Railway Email Fix - Complete Guide

## Problem
Railway blocks outbound SMTP connections on port 587, causing email verification to fail.

## Solution
Use SendGrid HTTP API (port 443) instead of SMTP (port 587).

---

## Step-by-Step Fix

### 1. Railway Environment Variables

Go to Railway → Your Project → Web Service → Variables

**DELETE these variables (if they exist):**
- EMAIL_HOST
- EMAIL_PORT  
- EMAIL_HOST_USER

**KEEP/ADD only these 2:**
```
EMAIL_HOST_PASSWORD=SG.your_actual_sendgrid_api_key_here
DEFAULT_FROM_EMAIL=FinTrack <shreyashpatil655@gmail.com>
```

### 2. Verify SendGrid Sender

1. Go to https://app.sendgrid.com
2. Settings → Sender Authentication
3. Verify a Single Sender
4. Add: shreyashpatil655@gmail.com
5. Check email and click verification link
6. Confirm it shows "Verified" with green checkmark

### 3. Deploy Code

```bash
git add .
git commit -m "fix: use SendGrid HTTP API to bypass Railway SMTP blocking"
git push
```

### 4. Test

1. Wait for Railway deployment to complete
2. Register a new user
3. Check Railway logs for:
   - "Using SendGrid HTTP API"
   - "SendGrid API response: 202"
   - "Email sent successfully via SendGrid API"

---

## Troubleshooting

### Still seeing "Connection timed out"?
- You still have EMAIL_HOST or EMAIL_PORT set in Railway
- Delete them and redeploy

### "Sender not verified" error?
- Go to SendGrid → Settings → Sender Authentication
- Verify your sender email

### "ImportError: No module named sendgrid"?
- Check requirements.txt has `sendgrid>=6.11.0`
- Railway should install it automatically

### Email not received?
- Check spam folder
- Check SendGrid Activity page
- Verify DEFAULT_FROM_EMAIL matches verified sender

---

## How It Works

**Before (SMTP - Blocked):**
```
Django → SMTP Port 587 → ❌ Railway Firewall → SendGrid
```

**After (HTTP API - Works):**
```
Django → HTTPS Port 443 → ✅ Railway Firewall → SendGrid
```

---

## Railway Variables Summary

Only 2 variables needed:

| Variable | Value | Purpose |
|----------|-------|---------|
| EMAIL_HOST_PASSWORD | SG.abc123... | SendGrid API key |
| DEFAULT_FROM_EMAIL | FinTrack <email@domain.com> | Verified sender |

**Do NOT set:** EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER (these force SMTP mode)
