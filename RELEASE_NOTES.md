# GFlow v0.1.20

Fixes media responses and model capability validation, and adds browser stage diagnostics without credentials.

- Reads inline media within the 128 MiB decoded limit, including file growth during reading; reduces large-media parsing overhead.
- Publishes reference image limits by actual video model and duration. Quality 8-second requests that do not support reference images explicitly reject them instead of silently dropping them.
- Browser startup, page load, and session operation errors retain safe stage and reason classifications. No Cookies, tokens, captcha parameters, or complete sensitive exceptions are logged; verification flow and retry policy remain unchanged.
- Preserves the 0.1.19 host SSE format, asynchronous responses, fixed accounts, and project binding.

Real-device limits: CutFlow 0.6.5 and GFlow 0.1.19 passed actual project creation and download-only recovery of existing images. One new-image request returned Failed to obtain reCAPTCHA token after 109.1 seconds and produced no output. A local blank-page startup check passed in ordinary Chrome, but does not prove Google verification pages work. New images and successive edits still require actual acceptance checks; this version does not claim to fix upstream verification.

On Windows, download gflow_0.1.20_windows_amd64.zip and extract gflow.dll. Exit the EasyCLIProxyAPI proxy, replace the plugin, preserve gflow-data, then reopen the proxy. CutFlow 0.6.6 is recommended. Do not delete accounts, projects, or existing outputs to retry.
