# Google Calendar Integration Setup

This guide explains how to set up Google Calendar integration with Gatherly.

## 🚀 **Features**

- **OAuth Authentication**: Secure connection to Google Calendar
- **Availability Sync**: Import busy times from Google Calendar to update your Gatherly availability
- **Event Creation**: Automatically add accepted Gatherly events to your Google Calendar
- **Privacy Control**: Full user control over sync settings

## 📋 **Setup Requirements**

### 1. Google Cloud Console Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the **Google Calendar API**:
   - Go to "APIs & Services" > "Library"
   - Search for "Google Calendar API"
   - Click "Enable"

### 2. Create OAuth Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth 2.0 Client IDs"
3. Configure the OAuth consent screen if prompted
4. Set application type to "Web application"
5. Add authorized redirect URIs:
   - `http://localhost:5006/auth/google/callback` (for development)
   - `https://yourdomain.com/auth/google/callback` (for production)

### 3. Environment Variables

Add the following to your `.env` file:

```bash
# Google Calendar API Configuration
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here
GOOGLE_REDIRECT_URI=http://localhost:5006/auth/google/callback

# Token encryption key (will be auto-generated if not provided)
GOOGLE_TOKEN_ENCRYPTION_KEY=your_encryption_key_here
```

## 🔧 **How It Works**

### **Authentication Flow**
1. User clicks "Connect Google Calendar" in Settings
2. Redirected to Google OAuth consent screen
3. User grants calendar permissions
4. Tokens are encrypted and stored securely
5. User can now sync availability and events

### **Availability Sync**
- **Manual Sync**: Click "Sync Availability" button in Settings
- **Smart Detection**: Busy times from Google Calendar mark you as unavailable
- **Default Hours**: Weekdays 9 AM - 5 PM available by default (if no conflicts)
- **Weekend Handling**: Weekends default to unavailable

### **Event Integration**
- **Auto-Add Events**: When you accept a Gatherly invitation, it's added to Google Calendar
- **Rich Details**: Includes event description, attendees, and reminders
- **Conflict Prevention**: Sync availability to avoid double-booking

## 🎯 **User Experience**

### **Settings Page**
- **Connection Status**: Shows if Google Calendar is connected
- **Sync Controls**: Toggle auto-sync and auto-add features
- **Manual Sync**: One-click availability sync button

### **Privacy & Control**
- **Granular Settings**: Choose what to sync and when
- **Easy Disconnect**: One-click to revoke access
- **Secure Storage**: All tokens encrypted at rest

## 🔒 **Security & Privacy**

- **Minimal Permissions**: Only requests necessary calendar scopes
- **Token Encryption**: Refresh tokens encrypted using Fernet encryption
- **User Control**: Easy disconnect and clear data retention policy
- **No Data Retention**: Only stores what's necessary for sync functionality

## 📱 **API Scopes Used**

```python
GOOGLE_SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',    # Read calendar events
    'https://www.googleapis.com/auth/calendar.events',     # Create/modify events  
    'https://www.googleapis.com/auth/calendar.freebusy'    # Check availability
]
```

## 🚨 **Troubleshooting**

### **Connection Issues**
- Verify Google Cloud Console credentials
- Check redirect URI matches exactly
- Ensure Google Calendar API is enabled

### **Sync Problems**
- Check user has granted all required permissions
- Verify tokens haven't expired (auto-refreshed)
- Check server logs for specific error messages

### **Development vs Production**
- Update redirect URIs for your domain
- Set proper `APP_BASE_URL` environment variable
- Use HTTPS in production

## 🎉 **Testing the Integration**

1. Start the Flask server: `python run.py`
2. Go to Settings page
3. Click "Connect Google Calendar"
4. Grant permissions
5. Try "Sync Availability" button
6. Create and accept an event to test auto-add

## 🔮 **Future Enhancements**

- **Two-way Sync**: Update Gatherly when Google Calendar events change
- **Multiple Calendars**: Sync from specific calendars
- **Smart Scheduling**: Suggest optimal meeting times
- **Conflict Resolution**: Handle overlapping events intelligently
- **Calendar Selection**: Choose which calendar to add events to

---

**Ready to connect your calendar?** Head to Settings and click "Connect Google Calendar"! 🗓️✨
