# Railway Deployment Instructions

## Prerequisites
1. Install Railway CLI: `npm install -g @railway/cli`
2. Create a Railway account at https://railway.app

## Deployment Steps

### 1. Login to Railway
```bash
railway login
```

### 2. Initialize Railway Project
```bash
railway init
```

### 3. Add PostgreSQL Database
```bash
railway add postgresql
```

### 4. Set Environment Variables
Set these environment variables in Railway dashboard or via CLI:

**Required:**
- `SECRET_KEY` - A secure random string for Flask sessions
- `DATABASE_URL` - Automatically set by Railway PostgreSQL service

**Optional (for SMS features):**
- `TWILIO_ACCOUNT_SID` - Your Twilio Account SID
- `TWILIO_AUTH_TOKEN` - Your Twilio Auth Token  
- `TWILIO_PHONE_NUMBER` - Your Twilio phone number

**Optional (for email features):**
- `MAIL_SERVER` - SMTP server (default: smtp.gmail.com)
- `MAIL_PORT` - SMTP port (default: 587)
- `MAIL_USERNAME` - Email username
- `MAIL_PASSWORD` - Email password/app password
- `MAIL_DEFAULT_SENDER` - Default sender email

**Optional (for Google Calendar integration):**
- `GOOGLE_CLIENT_ID` - Google OAuth Client ID
- `GOOGLE_CLIENT_SECRET` - Google OAuth Client Secret
- `GOOGLE_REDIRECT_URI` - Google OAuth redirect URI (https://yourdomain.railway.app/auth/google/callback)

### 5. Deploy
```bash
railway up
```

### 6. Run Database Migrations
After first deployment:
```bash
railway run flask db upgrade
```

## Environment Variables via CLI
```bash
railway variables set SECRET_KEY=your-secret-key-here
railway variables set TWILIO_ACCOUNT_SID=your-twilio-sid
railway variables set TWILIO_AUTH_TOKEN=your-twilio-token
railway variables set TWILIO_PHONE_NUMBER=your-twilio-number
```

## Post-Deployment
1. Your app will be available at the Railway-provided domain
2. Update Google OAuth redirect URI to match your Railway domain
3. Test all functionality including SMS and email features

## Troubleshooting
- Check logs: `railway logs`
- Connect to database: `railway connect postgresql`
- Run commands: `railway run <command>`
