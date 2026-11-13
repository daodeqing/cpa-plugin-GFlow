# GFlow login helper

Sync the current Chrome / Edge Google Flow login session to local EasyCPA.

## Installation and use

1. Download the [extension ZIP](https://github.com/daodeqing/cpa-plugin-GFlow/raw/main/downloads/GFlow-browser-extension.zip) and extract it. Enable Developer mode at `chrome://extensions/` (use `edge://extensions/` for Edge), then load the unpacked extension.
2. In EasyCPA, open GFlow, Add account, and click "Copy extension config". Paste it into the helper Quick import field and enter the current Google email.
3. Log in to [Google Flow](https://flow.google.com/projects) in the same browser profile and click "Save and sync now".

After the first save, the local connection settings are reused without pasting or entering credentials again. Automatic sync every 60 minutes requires the browser to remain running. Use separate browser profiles for multiple Google accounts.

## Costs and data

- The GFlow extension and source code are free. No separate GFlow account is required.
- Google Flow requires a Google account. Available free credits, regional requirements, subscriptions, and credits follow the Google website terms. This extension does not purchase paid subscriptions automatically.
- Third-party captcha services usually require registration, funds, and an API Key; local browser methods do not require purchasing a captcha service. Proxies may cost extra.
- Sync verifies login, queries credits, and may prepare a project; it does not start image or video generation.
- During sync, the extension observes only its own newly opened Flow tab and reads Cookies actually sent with the read-only credits request. It immediately removes the listener and closes the tab afterward; it does not observe other tabs. Login credentials are submitted only to the configured local GFlow API, sharing port 8317 by default.
- Pairing credentials remain only in local storage for the current extension, without Chrome sync. Saved complete credentials are not displayed after the page closes. Logs hide email addresses and credentials.

## Updates and troubleshooting

Current version **1.3.4**. Replace the program files in the original extension directory, then click "Reload" on the extension management page. Existing connection settings remain usable.

Version 1.3.4 adds webRequest permission to read Cookies actually sent with the current credits request. Reload the extension after updating. Browser credits checks are diagnostic only; the backend must still verify independently before saving the account.

Sync failures display a red message. "View sync logs" shows filtered error stages, RPCs, and status codes. "Cookies extracted" indicates only that reading completed; sync succeeds only after Google verification and account saving.

Source: [GFlow](https://github.com/daodeqing/cpa-plugin-GFlow/tree/main/browser-extension). API handling references Flow2API; GFlow is an independent adapter and does not imply official endorsement by Google or EasyCPA. Real-account sync is still under investigation; actual image and video generation have not been verified.
