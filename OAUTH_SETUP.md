# OAuth Setup Guide - Google & Microsoft Sign-In

This guide will help you set up Google and Microsoft OAuth authentication for your EduSync application.

## Prerequisites
- Authlib library (already added to requirements.txt)
- Google and/or Microsoft developer accounts
- Environment variable configuration

## Setup Instructions

### Step 1: Install Requirements

```bash
pip install -r requirements.txt
```

This will install `authlib` and `requests` needed for OAuth.

---

## Google OAuth Setup

### 1. Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click on the project dropdown at the top
3. Click "NEW PROJECT"
4. Enter a project name (e.g., "EduSync Student Management")
5. Click "CREATE"

### 2. Enable Google+ API

1. In the Cloud Console, go to "APIs & Services" > "Library"
2. Search for "Google+ API"
3. Click on it and click "ENABLE"

### 3. Create OAuth Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "CREATE CREDENTIALS" > "OAuth 2.0 Client ID"
3. If prompted, configure the OAuth consent screen first:
   - Choose "External" user type
   - Fill in the required fields (App name, User support email, etc.)
   - Add required scopes: `openid`, `email`, `profile`
4. For Application Type, select "Web application"
5. Add Authorized redirect URIs:
   - Development: `http://localhost:5000/authorize/google`
   - Production: `https://yourdomain.com/authorize/google`
6. Click "CREATE"
7. Copy the **Client ID** and **Client Secret**

### 4. Set Environment Variables

Create a `.env` file in your project root or set system environment variables:

```bash
# Windows PowerShell
$env:GOOGLE_CLIENT_ID="YOUR_GOOGLE_CLIENT_ID"
$env:GOOGLE_CLIENT_SECRET="YOUR_GOOGLE_CLIENT_SECRET"

# Windows CMD
set GOOGLE_CLIENT_ID=YOUR_GOOGLE_CLIENT_ID
set GOOGLE_CLIENT_SECRET=YOUR_GOOGLE_CLIENT_SECRET

# macOS/Linux
export GOOGLE_CLIENT_ID="YOUR_GOOGLE_CLIENT_ID"
export GOOGLE_CLIENT_SECRET="YOUR_GOOGLE_CLIENT_SECRET"
```

Or create a `.env` file and use python-dotenv:

```bash
pip install python-dotenv
```

Then add to `app.py` (after imports):
```python
from dotenv import load_dotenv
load_dotenv()
```

---

## Microsoft OAuth Setup

### 1. Register Your Application

1. Go to [Azure Portal](https://portal.azure.com/)
2. Search for "App registrations" and click on it
3. Click "New registration"
4. Name: Enter application name (e.g., "EduSync Student Portal")
5. Supported account types: Select "Accounts in any organizational directory (Any Azure AD directory - Multitenant)"
6. Redirect URI: 
   - Platform: "Web"
   - URL: `http://localhost:5000/authorize/microsoft` (for development)
7. Click "Register"

### 2. Configure API Credentials

1. In your app registration, go to "Certificates & secrets"
2. Click "New client secret"
3. Add a description (e.g., "EduSync OAuth Secret")
4. Expiration: Select 24 months (or as per your policy)
5. Click "Add"
6. **Copy the Value** (this is your Client Secret) - you won't see it again!

### 3. Configure API Permissions

1. Go to "API permissions"
2. Click "Add a permission"
3. Select "Microsoft Graph"
4. Click "Delegated permissions"
5. Search and select: `email`, `openid`, `profile`
6. Click "Add permissions"

### 4. Get Your Application IDs

1. Go to "Overview" tab
2. Copy the **Application (client) ID**
3. You already have **Client Secret** from step 2

### 5. Set Environment Variables

```bash
# Windows PowerShell
$env:MICROSOFT_CLIENT_ID="YOUR_MICROSOFT_CLIENT_ID"
$env:MICROSOFT_CLIENT_SECRET="YOUR_MICROSOFT_CLIENT_SECRET"

# Windows CMD
set MICROSOFT_CLIENT_ID=YOUR_MICROSOFT_CLIENT_ID
set MICROSOFT_CLIENT_SECRET=YOUR_MICROSOFT_CLIENT_SECRET

# macOS/Linux
export MICROSOFT_CLIENT_ID="YOUR_MICROSOFT_CLIENT_ID"
export MICROSOFT_CLIENT_SECRET="YOUR_MICROSOFT_CLIENT_SECRET"
```

---

## Production Deployment

### Important Security Notes:

1. **Never commit credentials** to version control
2. **Use environment variables** for storing secrets
3. **Update redirect URIs** in Google Cloud and Azure to match your production domain
4. **Use HTTPS** in production URLs

### Example Production Environment Variables:

For Google:
```
GOOGLE_CLIENT_ID=xxxx-xxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_google_secret
```

For Microsoft:
```
MICROSOFT_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
MICROSOFT_CLIENT_SECRET=your_microsoft_secret
```

---

## User Database

OAuth users are stored in the `oauth_users` table with the following information:
- **provider**: 'google' or 'microsoft'
- **provider_id**: Unique ID from OAuth provider
- **email**: User's email address
- **name**: User's full name
- **profile_pic**: Profile picture URL
- **user_type**: 'student' or 'admin' (default: 'student')
- **created_at**: Account creation timestamp

---

## Testing Locally

1. Set your environment variables
2. Run the application:
   ```bash
   python app.py
   ```
3. Visit `http://localhost:5000/login`
4. Click "Sign in with Google" or "Sign in with Microsoft"
5. You should be redirected to the OAuth provider and back to the dashboard

---

## Troubleshooting

### "Invalid Client ID" Error
- Verify your credentials are correct
- Check that environment variables are properly set
- Restart the Flask application after setting environment variables

### "Redirect URI Mismatch" Error
- Ensure the callback URL in Google Cloud/Azure matches your code
- For development: use `http://localhost:5000/authorize/google`
- For production: use your actual domain with HTTPS

### User Not Being Created
- Check that the oauth_users table exists in your database
- Verify database is writable
- Check browser console for error messages

### Login Keeps Redirecting
- Sessions might not be persisting correctly
- Check that `app.secret_key` is set properly
- Verify cookies are enabled

---

## Additional Resources

- [Authlib Documentation](https://docs.authlib.org/)
- [Google OAuth Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Microsoft Identity Platform](https://docs.microsoft.com/en-us/azure/active-directory/develop/)

---

## Next Steps

After setting up OAuth, consider:
1. Implementing account linking (connect traditional login with OAuth)
2. Adding user profile management
3. Implementing password reset via email
4. Adding two-factor authentication
5. Social login user preferences
