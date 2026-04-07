# OAuth Implementation - Setup Quick Guide

## ✅ What's Been Added

### 1. **Backend Changes (app.py)**
- OAuth authentication routes for Google and Microsoft
- New `oauth_users` database table to store OAuth user information
- Environment variable support via `.env` files
- Automatic user creation on first OAuth login
- Session management for OAuth users

### 2. **Frontend Changes (login.html)**
- "Sign in with Google" button
- "Sign in with Microsoft" button
- Beautiful gradient styling with hover effects
- Divider line separating social login from traditional login

### 3. **Dependencies Updated**
```
authlib>=1.2.0        - OAuth client library
requests>=2.28.0      - HTTP requests
python-dotenv>=0.21.0 - Environment variable management
```

### 4. **Configuration Files**
- `.env.example` - Template for environment variables
- `OAUTH_SETUP.md` - Comprehensive setup guide
- Updated `README.md` - Project documentation

---

## 🚀 Next Steps to Get It Working

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Set Up OAuth Credentials

**For Google:**
1. Visit [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Copy Client ID and Client Secret

**For Microsoft:**
1. Visit [Azure Portal](https://portal.azure.com/)
2. Go to App registrations
3. Register a new application
4. Add client secret
5. Configure API permissions (email, openid, profile)

### Step 3: Configure Environment Variables

**Option A: Using .env file (Recommended)**
```bash
# Copy the template
cp .env.example .env

# Edit .env with your credentials
GOOGLE_CLIENT_ID=your_google_id
GOOGLE_CLIENT_SECRET=your_google_secret
MICROSOFT_CLIENT_ID=your_microsoft_id
MICROSOFT_CLIENT_SECRET=your_microsoft_secret
```

**Option B: System Environment Variables**

Windows PowerShell:
```powershell
$env:GOOGLE_CLIENT_ID="your_google_id"
$env:GOOGLE_CLIENT_SECRET="your_google_secret"
$env:MICROSOFT_CLIENT_ID="your_microsoft_id"
$env:MICROSOFT_CLIENT_SECRET="your_microsoft_secret"
```

Windows CMD:
```cmd
set GOOGLE_CLIENT_ID=your_google_id
set GOOGLE_CLIENT_SECRET=your_google_secret
set MICROSOFT_CLIENT_ID=your_microsoft_id
set MICROSOFT_CLIENT_SECRET=your_microsoft_secret
```

### Step 4: Start the Application
```bash
python app.py
```

### Step 5: Test the Login
1. Go to http://localhost:5000/login
2. Click "Sign in with Google" or "Sign in with Microsoft"
3. Authorize the application
4. You should be logged in!

---

## 📋 Important Configuration Notes

### Redirect URIs

**For Google (in Google Cloud Console):**
- Development: `http://localhost:5000/authorize/google`
- Production: `https://yourdomain.com/authorize/google`

**For Microsoft (in Azure Portal):**
- Development: `http://localhost:5000/authorize/microsoft`
- Production: `https://yourdomain.com/authorize/microsoft`

### Features Included

✅ User auto-registration on first OAuth login
✅ Profile picture storage
✅ Email verification
✅ Role-based access (students by default)
✅ Session management
✅ Error handling and logging
✅ Support for multiple OAuth providers

---

## 🔒 Security Features

- OAuth tokens are handled securely via Authlib
- No passwords are stored for OAuth users
- Unique constraint on (provider, provider_id) prevents duplicate accounts
- Environment variables for credentials (never hardcoded)
- CSRF protection built into Authlib

---

## 📊 Database Schema

New `oauth_users` table structure:
```
id              - Unique ID
provider        - 'google' or 'microsoft'
provider_id     - Unique ID from OAuth provider
email           - User's email
name            - User's full name
profile_pic     - Profile picture URL
user_type       - 'student' or 'admin' (default: student)
created_at      - Account creation timestamp
```

---

## ⚠️ Troubleshooting

### Issue: "Invalid Client ID"
- Ensure environment variables are set correctly
- Restart the Flask application after setting env vars
- Check that credentials match what's in Google/Azure console

### Issue: "Redirect URI Mismatch"
- Update the redirect URIs in Google Cloud Console and Azure Portal
- Make sure URLs exactly match (http vs https, port number, path)

### Issue: User Not Created
- Check that the database is writable
- Verify oauth_users table exists: `SELECT * FROM sqlite_master WHERE type='table' AND name='oauth_users';`
- Check browser console for JavaScript errors

### Issue: "Unauthorized" or Loop
- Clear browser cookies
- Check that Flask secret key is set
- Ensure session configuration is correct

---

## 📚 Additional Resources

- [OAUTH_SETUP.md](OAUTH_SETUP.md) - Detailed setup instructions
- [Authlib Docs](https://docs.authlib.org/en/latest/)
- [Google OAuth 2.0](https://developers.google.com/identity/protocols/oauth2)
- [Microsoft Identity Platform](https://docs.microsoft.com/en-us/azure/active-directory/develop/)

---

## ✨ Future Enhancements

Consider implementing:
1. Account linking (connect OAuth with traditional login)
2. User profile management page
3. OAuth refresh token handling
4. Custom user roles for OAuth signins
5. Two-factor authentication
6. Social profile data synchronization

---

**Your system now has modern OAuth authentication! 🎉**
