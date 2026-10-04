# Google API Scopes & OAuth Configuration

## ⚠️ Important Note: Sensitive Data Scopes

The **Google Calendar API** (`https://www.googleapis.com/auth/calendar`) is considered **"sensitive" data** by Google Cloud.

Because the Agentic Personal Porter acts on behalf of the user to read, update, and manage their calendar events, we are requesting sensitive scopes during the OAuth 2.0 Authorization Code flow.

### Development Phase
During development:
- The OAuth Consent Screen must be configured with "Testing" status.
- Only users explicitly listed as **"Test Users"** in the Google Cloud Console (e.g., both Business and Personal emails) will be able to grant calendar access.
- Test users will see an "Unverified App" warning screen during login. They must click "Advanced" -> "Go to app (unsafe)" to bypass it.

### Production Phase
Before "publishing" the app for real production use (where any user can log in without being added to the Test Users list):
- The application **must go through Google's full verification process**.
- This involves submitting a video demonstrating how the calendar data is used, providing a Privacy Policy, and justifying the need for the `https://www.googleapis.com/auth/calendar` scope.
