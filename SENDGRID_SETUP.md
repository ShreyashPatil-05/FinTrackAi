# SendGrid Email Setup Guide

## Why SendGrid?
Railway blocks direct SMTP connections to Gmail for security reasons. SendGrid is a reliable email delivery service with a free tier (100 emails/day).

## Setup Steps

### 1. Create SendGrid Account
1. Go to https://sendgrid.com/free/
2. Sign up with your email
3. Verify your email address
4. Complete the onboarding wizard:
   - Role: Developer
   - Purpose: Transactional emails
   - Volume: Less than 1,000/month

### 2. Create API Key
1. Log in to SendGrid dashboard
2. Click **Settings** (left sidebar)
3. Click **API Keys**
4. Click **Create API Key**
5. Settings:
   - Name: `FinTrack`
   - Permissions: **Full Access**
6. Click **Create & View**
7. **COPY THE API KEY** (starts with `SG.`)
   - You'll only see it once!
   - Save it temporarily in a text file

### 3. Configure Railway Environment Variables
1. Go to https://railway.app
2. Open your FinTrack project
3. Click on your Web service
4. Go to **Variables** tab
5. Add/Update these variables:

```
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=<paste-your-sendgrid-api-key>
```

**Important**: 
- `EMAIL_HOST_USER` should be literally the word `apikey`
- `EMAIL_HOST_PASSWORD` should be your actual SendGrid API key (the `SG.abc123...` string)

### 4. Deploy Changes
1. Commit the code changes:
   ```bash
   git add .
   git commit -m "feat: enable email verification with SendGrid support"
   git push
   ```

2. Railway will automatically redeploy with the new settings

### 5. Test Email Verification
1. Go to your Railway app URL
2. Register a new user
3. Check the email inbox (the one you registered with)
4. Click the verification link
5. You should be able to log in!

## Troubleshooting

### Emails not sending?
1. Check Railway logs for errors
2. Verify all 4 environment variables are set correctly
3. Make sure the API key is correct (no extra spaces)
4. Check SendGrid dashboard for activity/errors

### "Invalid API key" error?
- The API key might have been copied incorrectly
- Create a new API key in SendGrid and update Railway

### Emails going to spam?
- This is normal for new SendGrid accounts
- To fix: Set up domain authentication in SendGrid (optional, for production)

## Local Development
For local testing, the app still uses Gmail SMTP (configured in `.env`). SendGrid is only used on Railway.

## Free Tier Limits
- 100 emails per day
- Perfect for testing and small apps
- Upgrade to paid plan if you need more

## Support
- SendGrid docs: https://docs.sendgrid.com
- SendGrid support: https://support.sendgrid.com
