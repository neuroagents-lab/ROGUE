# Google Drive Setup Guide

This guide sets up the Google account and Drive OAuth files used by ROGUE's `restrictedaccess` scenario examples.

## Repo files

- `evaluation_examples/settings/google/settings.json.template`: template for the Gmail login file.
- `evaluation_examples/settings/google/settings.json`: the Gmail and password used for the Chrome login step.
- `evaluation_examples/settings/googledrive/client_secrets.json`: the OAuth client secret downloaded from Google Cloud.
- `evaluation_examples/settings/googledrive/settings.yml`: the PyDrive config already in this repo.
- `evaluation_examples/settings/googledrive/credentials.json`: the OAuth token saved after you authorize Google Drive.

Use `evaluation_examples/settings/google/settings.json` for the Gmail login, and use the `evaluation_examples/settings/googledrive/` files for Drive OAuth.

## 1. Register A Blank Google Account

1. Go to [Google signup](https://accounts.google.com/signup) and register a blank new account.
   - You do not need to provide any recovery email or phone for testing.
   - Ignore any security recommendations.
   - Turn off [2-Step Verification](https://support.google.com/accounts/answer/1064203?hl=en&co=GENIE.Platform%3DDesktop#:~:text=Open%20your%20Google%20Account.,Select%20Turn%20off.) to avoid setup failures.

2. Use a private account, not a shared one.

3. Copy `evaluation_examples/settings/google/settings.json.template` to `evaluation_examples/settings/google/settings.json`.
4. Replace the placeholder email and password in `settings.json` with your own account details.

```json
{
  "email": "your_google_account@gmail.com",
  "password": "your_google_account_password"
}
```

## 2. Create A Google Cloud Project

1. Open [Google Cloud Project Creation](https://console.cloud.google.com/projectcreate) and create a new project.
   - Any project name is fine.

2. Open the [Google Drive API console](https://console.cloud.google.com/apis/library/drive.googleapis.com?) and enable the Google Drive API for that project.

## 3. Configure OAuth Consent Screen

Open the [OAuth consent screen](https://console.cloud.google.com/apis/credentials/consent) page and do the following:

1. Choose **External** as the user type and click **CREATE**.

2. Fill in the app information.
   - App name: any name you like.
   - User support email: your Gmail address.
   - Developer contact information: your Gmail address.
   - Leave other fields blank if the form allows it.
   - Click **SAVE AND CONTINUE**.

3. Add scopes.
   - Click **ADD OR REMOVE SCOPES**.
   - Select `https://www.googleapis.com/auth/drive`.
   - Click **UPDATE** and **SAVE AND CONTINUE**.

4. Add test users.
   - Click **ADD USERS**.
   - Add the same Gmail address you used above.
   - Click **SAVE AND CONTINUE**.

## 4. Publish The App

Publish the app after finishing the consent screen so the refresh token lasts longer. Without publishing, the refresh token is only valid for 7 days.

## 5. Create OAuth2.0 Credentials

1. Go to the [Credentials](https://console.cloud.google.com/apis/credentials) page.
2. Click **CREATE CREDENTIALS** -> **OAuth client ID**.
3. Select **Desktop app** as the application type.
4. Give it any name.
5. Click **CREATE**.
6. Download the JSON file. Google will usually name it something like `client_secret_xxxxx.json`.
7. Save it as `evaluation_examples/settings/googledrive/client_secrets.json`.

The repo uses `evaluation_examples/settings/googledrive/settings.yml` to point PyDrive at that file and to save the authorized token in `evaluation_examples/settings/googledrive/credentials.json`. You usually do not need to edit `settings.yml` unless you move files.

## 6. Authorize Google Drive Once

The first time you run a task that uses Google Drive, you will see a permission URL.

1. Open the link in unsafe mode.
2. Use the Gmail address from `evaluation_examples/settings/google/settings.json`.
3. Approve access.
4. Confirm the choice once.

When it finishes, you should see `The authentication flow has completed.` on a blank page.

## 7. Common Problems

1. `Access blocked: OSWorld's request is invalid`
   - Add your Gmail address as a test user in the OAuth consent screen.

2. Application does not have the needed permissions
   - Verify that `https://www.googleapis.com/auth/drive` is included in the consent screen scope list.

3. Phone verification code required
   - This can happen when you use a new IP or device.
   - Enter any phone number, use the received code, and then restart the task.

4. Identity verification
   - This usually means Google will not offer the phone-code path.
   - Reset the password from the device where the account was created.
   - If you change the password, update `evaluation_examples/settings/google/settings.json`.

5. Avoid frequent IP or device changes
   - Google may keep flagging the account if your login location changes often.
