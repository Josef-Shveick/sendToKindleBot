# sendToKindleBot

Documents (.epub and .txt) and generated HTML articles from the exact Telegram
username `Josef_Shveick` are sent to Dropbox. All other usernames retain the
existing Kindle email delivery. Dropbox errors are reported to the user and do
not fall back to email.

Configure these environment variables in local `secrets.env`, or in the
`Variables` object of the deployment's `LAMBDA_SECRETS_JSON` GitHub secret
(the same format as `secrets.json`):

| Variable | Value |
| --- | --- |
| `DROPBOX_REFRESH_TOKEN` | Your Dropbox app's refresh token (required). |
| `DROPBOX_APP_KEY` | The key of the app that issued the token (required). |
| `DROPBOX_APP_SECRET` | That app's secret; required for confidential-client OAuth, omitted for tokens obtained using PKCE without a client secret. |
| `DROPBOX_FOLDER` | Destination folder, e.g. `/Books`; defaults to the app's accessible root. |

For an App Folder app, paths are relative to its Dropbox app folder: `/Books`
means `Apps/<app name>/Books`. Configure the intended destination folder before
running the bot. Keep credentials out of source control. Existing SMTP settings
remain required for the other users and for application startup.

Each delivery exchanges the refresh token for a short-lived access token using
[Dropbox OAuth](https://developers.dropbox.com/oauth-guide), then uploads the
original bytes using the [upload endpoint](https://docs.dropboxapi.com/dropbox-api/api-reference/user-endpoints/files/upload).
The token needs `files.content.write`. Duplicate filenames are automatically
renamed instead of overwriting existing files. Files larger than 150 MB are
rejected by this integration; Telegram's download limits also apply.

Run checks with `python -m pytest` after installing `requirements.txt` and
`requirements-dev.txt`. The current tests check imports and the Lambda handler;
they do not verify Dropbox delivery or send files.
