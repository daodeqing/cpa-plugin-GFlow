# GFlow

[Chinese README](README.zh-CN.md)

Use Google Flow image / video models on the same port as EasyCPA, default 8317.

## CutFlow project and session binding (v0.1.12)

The new `gflow-project-control` endpoint accepts ordinary generation API Keys. Creating and querying projects does not call image or video models or require clients to store management keys. New CutFlow projects can bind to actual Google Flow projects. Sessions within a project share a fixed account and project, and the client explicitly supplies the selected reference image for successive edits. An expired account or insufficient tier does not silently switch accounts or rotate projects. Hide the control model from image/video selectors; the seven media models remain unchanged.

Project creation uses SQLite for persistent idempotency. Timeouts, cancellation, or lost acknowledgments mark creation as requiring verification, without automatic recreation. The old project pool is preserved during migration; CutFlow-specific projects do not enter rotation for other clients. See [Project control protocol, parameter capabilities, and permission boundaries](docs/project-control-v1.md).

## Add accounts with browser sync (recommended)

1. In GFlow, click "Add account", then "Copy download URL". Paste it into the Chrome / Edge address bar and press Enter to download the **GFlow login helper**, then extract it. Enable "Developer mode" on the Chrome / Edge extension management page and load the extracted folder.
2. In the same window, click "Copy extension config". Open the browser extension, paste the config, and enter the current Google email.
3. Log in to Google Flow in that browser, click "Save and sync now" in the extension, then return to GFlow and refresh the account list.

The EasyCPA embedded window restricts direct downloads and opening new windows, so the download and source links copy their URLs instead. The download URL uses the locally installed extension package and does not require GitHub access. If copying is restricted, a URL appears for manual copying.

After setup, sync with one click or automatically every 60 minutes. Automatic sync requires the browser to remain running. Use separate browser profiles for multiple Google accounts.

- [Extension GitHub source and installation instructions](https://github.com/daodeqing/cpa-plugin-GFlow/tree/main/browser-extension)
- [Download the GFlow login helper ZIP directly](https://github.com/daodeqing/cpa-plugin-GFlow/raw/refs/heads/main/downloads/GFlow-browser-extension.zip)

## If extension sync fails

The latest extension version is **1.3.4**. Download it again from "Add account" and replace the original extension folder. Click "Reload" on the Chrome / Edge extension management page; existing connection settings are preserved. Repository updates do not automatically update an older folder extracted separately for the browser.

Version 1.3.4 adds the `webRequest` permission. It reads Cookies actually sent with the credits request only in the Flow tab created for this sync and queries credits once. When sync ends, it removes the listener and closes the temporary tab. Reload the extension after updating. Browser and backend verification are separate; success appears only after the backend verifies and saves the account.

Errors and logs distinguish local connection, Google authentication, timeout, API changes, and project preparation failures without exposing Cookies or keys. Actual account sync and backend credit queries after saving have been verified locally; actual generation has not been verified.

## Supported models and API usage

There are **7 core base models, shown in the media selector, plus a dedicated project control endpoint**. This avoids filling client dropdowns with dozens of variants. When clients select parameters in the UI, the backend **automatically selects** the underlying Cartesian-product model:

### 1. Core models selected by clients (7 media models)

- **Image models (3)**:
  - `gflow-nano-banana-pro`: Nano Banana Pro (GEM_PIX_2, automatic selection for 1:1, 16:9, 9:16, 4:3, 3:4 and 1K/2K/4K)
  - `gflow-nano-banana-2-lite`: Nano Banana 2 Lite (HARBOR_SEAL, automatic selection for 5 aspect ratios and 1K/2K/4K)
  - `gflow-nano-banana-2.1`: Nano Banana 2.1 (BELUGA, automatic selection for 5 aspect ratios and 1K/2K/4K)
- **Video models (4)**:
  - `gflow-omni-1.1-flash`: Omni 1.1 Flash (automatic selection for 4s/6s/8s/10s durations and landscape/portrait, with native support for multiple reference images)
  - `gflow-veo-3.1-lite`: Veo 3.1 - Lite (automatic selection for 4s/6s/8s durations and landscape/portrait)
  - `gflow-veo-3.1-fast`: Veo 3.1 - Fast (automatic selection for 4s/6s/8s durations and landscape/portrait)
  - `gflow-veo-3.1-quality`: Veo 3.1 - Quality (automatic selection for 4s/6s/8s durations and landscape/portrait)

### 2. Automatic parameter selection (Auto-dispatch)

When clients select one of these 7 models, the backend resolves the model from request parameters:

- **Image selection**: Uses the selected `aspectRatio` (1:1, 16:9, 9:16, 4:3, 3:4) or OpenAI `size` (such as 1024x1024 or 1792x1024), plus resolution `imageSize` (1K, 2K, 4K) or OpenAI `quality` (standard, medium, hd, high), to select one of 45 underlying combinations. Defaults to 16:9 standard 1K when unspecified.
- **Video selection**: Uses duration (4s, 6s, 8s, 10s), orientation (16:9 landscape, 9:16 portrait), and reference image presence (automatically uses I2V/R2V) to select one of 26 underlying video combinations. Defaults to 8s 16:9 landscape when unspecified.

### 3. Preserved underlying Cartesian-product variants (direct and function calls)

All underlying combinations remain available. Third-party clients or agents can still pass an explicit variant name or call a function for direct matching and execution:

- **Image variants (3 base models x 5 aspect ratios x 3 resolutions = 45)**:
  - Examples include `gflow-nano-banana-2.1-square-4k` (1:1 4K), `gflow-nano-banana-pro-portrait-2k` (9:16 2K), and `gflow-nano-banana-2-lite-four-three` (4:3 1K).
- **Video variants (3 Veo families x 3 durations x 2 orientations + Omni 4 durations x 2 orientations = 26)**:
  - Examples include `gflow-veo-3.1-fast-4s-portrait` (4s portrait) and `gflow-omni-1.1-flash-10s-landscape` (10s landscape).
- The backend also supports legacy Gemini aliases such as `gflow-gemini-3.1-flash-image-square` and numeric aspect-ratio names such as `-16-9` and `-1-1`.

## You can also paste manually

In GFlow, open Add account, then "Method 2: Paste manually". Copy complete Cookies or Cookie JSON; Session Tokens are also accepted. Prefer the extension if newer Flow pages lack the old Token field. Expand the help below the input for the F12 retrieval steps.

## First installation settings

After installing from the plugin store, open GFlow directly. Official release packages embed an independent Python backend, Python runtime, and required dependencies in the dynamic library. No Python installation is required, and the plugin does not use a source directory on the developer computer.

Log in to the CPA management center in the same browser and remember the login. The GFlow static page reads management credentials from same-origin `cli-proxy-auth`, supporting the current obfuscated storage format. It sends credentials only to `/v0/management/plugins/gflow/` on the current host and no longer returns management keys through public resource APIs. In embedded desktop windows without shared browser storage, expand "Connect to management center manually". The temporary key stays only in page memory and clears when the page closes.

The default data directory is `gflow-data` beside the installed plugin dynamic library. It contains the database, media cache, backend logs, and versioned extracted runtimes. Advanced settings can point `data_dir` to an existing data directory; back it up before upgrading. Legacy `management_key` and `python_path` settings are no longer used. The software does not automatically read old developer directories or account data from other installations.

When a Windows host uses a temporary dynamic library copy, the default data directory is `plugins/gflow/gflow-data` beside the core executable, keeping account data out of temporary process directories. Since v0.1.11, management status reads and generation use separate request channels. Console auto-refresh reads only status and accounts without overwriting unsaved settings.

Browsers such as Chrome/Edge are not bundled. Local browser captcha methods still require an available browser; you can also configure a supported captcha service. The plugin backend communicates with the host through standard input/output without adding an external service port.

Public resource APIs serve only the management page and static login helper ZIP. Manual downloads of cached media use the authenticated management API `/v0/management/plugins/gflow/api/media?file=<filename>`. Local images and videos in generation responses become data URIs, so clients do not need management keys. The inline limit is 128 MiB per media item. Larger items produce an explicit instruction to retrieve the cache through the authenticated API, without resubmitting generation.

"Copy extension config" includes management credentials. Paste it only into the local GFlow login helper. The extension saves it in chrome.storage.local without Chrome sync; Clear config removes the saved data. Do not publish Cookies or extension connection settings.

## Free and paid costs

GFlow and the browser extension are free. Google Flow subscriptions and generation credits, paid captcha services, and proxies cost extra. Local browser captcha solving has no platform service fee but requires a working browser environment.

Adding / syncing an account verifies the login session, queries credits, and may create a project; it does not automatically generate images or videos. Sync does not enable disabled accounts.

## Verification scope

Fake data tests cover extension Cookie scope, sync authentication, account addition and updates, duplicate task coalescing, and page connections. The extension was installed locally and its file version checked. Local verification on October 16, 2026: login helper 1.3.4 successfully synced a real account, which was saved and enabled. The backend independently queried credits using the saved login session. Actual image / video generation has not been verified.

## Sources

The model adapter code embedded in GFlow references [TheSmallHanCat/flow2api](https://github.com/TheSmallHanCat/flow2api) and retains its MIT notice. The GFlow login helper is independently implemented and does not copy third-party browser extension source without a declared license.


### Generation lifecycle repair

Generation requests are attempted once and have bounded CAPTCHA/overall timeouts. Windows clients can stop their own request through a request-specific named pipe; queued cancellation cannot close the active browser. The dedicated browser runs headless and is reclaimed after the task. Python requires psutil for process ownership checks.

Cookie injection preserves explicit site scopes and handles legacy three-site mirrors without copying Flow-only OSID cookies to Google Accounts. Account sync and quota checks do not verify CAPTCHA readiness. Local preflight now obtains an IMAGE_GENERATION reCAPTCHA token after preserving cookie scopes, enabling native Trusted Types and executing the score-based key directly. A token check alone does not prove successful media generation.
