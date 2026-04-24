# Railway Deployment Checklist

## ✅ Pre-Deployment Verification

### 1. Code Changes
- [x] Email verification re-enabled in `accounts/views.py`
- [x] Settings support both Gmail (dev) and SendGrid (prod)
- [x] All deployment files configured correctly

### 2. Deployment Files Status
- [x] `railway.toml` - Configured with migrations
- [x] `Procfile` - Gunicorn with proper workers
- [x] `nixpacks.toml` - Static files collection
- [x] `requirements.txt` - All dependencies listed
- [x] `fintrack/settings_prod.py` - SITE_ID=2, security headers

### 3. Required Railway Environment Variables

**Already Set:**
- [x] `DJANGO_SETTINGS_MODULE=fintrack.settings_prod`
- [x] `DATABASE_URL` (auto-provided by PostgreSQL plugin)
- [x] `ALLOWED_HOSTS=web-production-95045.up.railway.app`
- [x] `SECRET_KEY`
- [x] `RECAPTCHA_SITE_KEY`
- [x] `RECAPTCHA_SECRET_KEY`

**Need to Add (SendGrid):**
- [ ] `EMAIL_HOST=smtp.sendgrid.net`
- [ ] `EMAIL_PORT=587`
- [ ] `EMAIL_HOST_USER=apikey`
- [ ] `EMAIL_HOST_PASSWORD=<your-sendgrid-api-key>`

---

## 📋 Deployment Steps

### Step 1: Get SendGrid API Key
1. Go to https://sendgrid.com/free/
2. Sign up and verify email
3. Settings → API Keys → Create API Key
4. Name: `FinTrack`, Permission: Full Access
5. Copy the API key (starts with `SG.`)

### Step 2: Add Environment Variables to Railway
1. Go to Railway dashboard
2. Open your FinTrack project
3. Click on Web service
4. Go to Variables tab
5. Add the 4 SendGrid variables listed above

### Step 3: Deploy Code Changes
```bash
git add .
git commit -m "feat: enable email verification with SendGrid support"
git push
```

### Step 4: Verify Deployment
1. Wait for Railway to finish deploying (1-2 minutes)
2. Check deployment logs for errors
3. Visit your app URL: https://web-production-95045.up.railway.app

### Step 5: Test Email Verification
1. Register a new test user
2. Check email inbox for verification link
3. Click the link to verify
4. Try logging in

---

## 🔍 Post-Deployment Verification

### Check These:
- [ ] App loads without errors
- [ ] Registration form works
- [ ] Email is sent (check inbox)
- [ ] Verification link works
- [ ] Login works after verification
- [ ] Dashboard loads correctly
- [ ] No errors in Railway logs

### Railway Logs
To view logs:
1. Railway dashboard → Your project
2. Click on Web service
3. Click "View Logs" or "Deployments" tab
4. Look for any errors or warnings

---

## 🚨 Troubleshooting

### Email Not Sending?
**Check:**
1. All 4 EMAIL_* variables are set in Railway
2. API key is correct (no extra spaces)
3. Railway logs for error messages
4. SendGrid dashboard for activity

**Common Issues:**
- Wrong API key → Create new one in SendGrid
- Missing variables → Double-check all 4 are set
- Typo in EMAIL_HOST_USER → Must be literally `apikey`

### Deployment Failed?
**Check:**
1. Railway build logs for errors
2. All dependencies in `requirements.txt`
3. Database migrations ran successfully
4. Static files collected

### Site Not Loading?
**Check:**
1. ALLOWED_HOSTS includes your Railway domain
2. SITE_ID=2 in production settings
3. Database is connected
4. No migration errors

---

## 📊 Deployment Configuration Summary

### Current Setup
- **Platform:** Railway
- **Database:** PostgreSQL (Railway plugin)
- **Web Server:** Gunicorn (2 workers, 2 threads)
- **Static Files:** WhiteNoise
- **Email:** SendGrid SMTP
- **Domain:** web-production-95045.up.railway.app

### Build Process
1. Railway detects push to main branch
2. Runs `nixpacks` build
3. Collects static files
4. Runs database migrations (preDeployCommand)
5. Starts Gunicorn server
6. Health check on port 8000

### Environment
- Python 3.12
- Django 6.0.2
- PostgreSQL 15+
- Node.js (for build tools)

---

## 📝 Notes

- **Local Development:** Uses Gmail SMTP (from `.env`)
- **Production:** Uses SendGrid SMTP (from Railway variables)
- **Email Limit:** 100 emails/day (SendGrid free tier)
- **Migrations:** Run automatically on each deploy
- **Static Files:** Served by WhiteNoise (no CDN needed)

---

## 🔗 Useful Links

- **Railway Dashboard:** https://railway.app
- **SendGrid Dashboard:** https://app.sendgrid.com
- **App URL:** https://web-production-95045.up.railway.app
- **Admin Panel:** https://web-production-95045.up.railway.app/admin

---

## ✅ Ready to Deploy!

Once you've:
1. ✅ Added SendGrid API key to Railway variables
2. ✅ Committed and pushed the code changes

Your app will automatically redeploy with email verification enabled!

**Estimated deployment time:** 2-3 minutes
