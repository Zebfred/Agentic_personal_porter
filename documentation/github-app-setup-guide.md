# Setting up a Custom GitHub App for Gemini Code Reviews

By creating a custom GitHub App, you grant the Gemini AI its own dedicated identity (e.g., "Zebfred's Review Bot") and strictly limit its access to only what it needs, bypassing the broad `GITHUB_TOKEN`.

Follow these steps to create and configure the app.

## Step 1: Create the GitHub App

1. Go to your GitHub Settings: Click your profile picture in the top right -> **Settings**.
2. On the left sidebar, scroll down and click **Developer settings**.
3. In the left sidebar, click **GitHub Apps**, then click the **New GitHub App** button.
4. Fill out the basic details:
   - **GitHub App name**: Give it a fun name! (e.g., `Zebfreds Agentic Reviewer`). *Note: This name must be globally unique across GitHub, so you might need to add a unique suffix.*
   - **Description**: "AI Code Review Bot powered by Gemini."
   - **Homepage URL**: You can just put the URL to your GitHub profile or repository.
   - **Webhook**: Uncheck the **Active** box under Webhook (we don't need webhooks for this, Actions will trigger the bot).
5. Set the Permissions:
   Scroll down to the **Repository permissions** section and set the following:
   - **Contents**: `Read-only` (Needed to read the code).
   - **Pull requests**: `Read & write` (Needed to post review comments).
   - **Issues**: `Read & write` (Optional, if you want it to comment on issues).
6. Scroll all the way to the bottom and click **Create GitHub App**.

## Step 2: Generate the Private Key and Note the App ID

You should now be on the settings page for your newly created App.

1. **Note the App ID**: At the top of the General page, you will see an **App ID** (a number like `123456`). Copy this down; you will need it shortly.
2. **Generate a Private Key**: Scroll down to the **Private keys** section and click **Generate a private key**.
3. A `.pem` file will automatically download to your computer. Open this file in a text editor (like VS Code or Notepad) so you can copy its contents in Step 4.

## Step 3: Install the App on Your Repository

1. On the left sidebar of your App's settings, click **Install App**.
2. Click **Install** next to your username.
3. Select **Only select repositories** and pick `Agentic_personal_porter`.
4. Click **Install**. 

## Step 4: Add the Variables and Secrets to Your Repository

Now you need to hand the App ID and Private Key over to your repository so the GitHub Action can authenticate as the bot.

1. Go to your `Agentic_personal_porter` repository on GitHub.
2. Click **Settings** > **Secrets and variables** > **Actions**.
3. **Add the App ID as a Variable**:
   - Click the **Variables** tab (next to the Secrets tab).
   - Click **New repository variable**.
   - Name: `APP_ID`
   - Value: Paste the numeric App ID you copied in Step 2.
   - Click **Add variable**.
4. **Add the Private Key as a Secret**:
   - Click the **Secrets** tab.
   - Click **New repository secret**.
   - Name: `APP_PRIVATE_KEY`
   - Value: Paste the *entire* contents of the `.pem` file you downloaded (including the `-----BEGIN RSA PRIVATE KEY-----` and `-----END RSA PRIVATE KEY-----` lines).
   - Click **Add secret**.

> [!IMPORTANT]
> **Don't Forget the Gemini API Key!**
> While you are on the Secrets page, make sure you also add a secret named `GEMINI_API_KEY` containing your actual Google Gemini API key. The GitHub App allows the bot to post to GitHub, but it still needs the API key to talk to the AI model!

## Step 5: Test it out!

You are fully configured! Because your `.github/workflows/gemini-review.yml` is already coded to look for `vars.APP_ID` and `secrets.APP_PRIVATE_KEY`, it will automatically detect them on your next PR. 

Create a test Pull Request, and you should see a code review posted proudly by your custom bot!
