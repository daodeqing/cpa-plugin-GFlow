# GFlow project control protocol v1 (plugin 0.1.12)

Project control reuses `POST /v1/chat/completions` with an ordinary generation API Key, without a management key. The dedicated `gflow-project-control` model performs control operations only and never enters the image/video generator. The seven existing media models and unbound third-party requests retain their behavior; clients must exclude the control model from media selectors.

Requests must use `stream: false` and contain one user message with a JSON string as content:

```json
{
  "model": "gflow-project-control",
  "stream": false,
  "messages": [{
    "role": "user",
    "content": "{\"version\":1,\"op\":\"capabilities\",\"workspaceId\":\"11111111-1111-4111-8111-111111111111\"}"
  }]
}
```

Control JSON:

- `version: 1`, `op`, and `workspaceId` are required; workspace and project IDs are UUIDs.
- `capabilities` requires no account and returns `models`, the service instance, and `projectBinding` capability. The base 1K catalog remains available without accounts; this response does not establish login or successful generation.
- `projects.list` returns projects registered in that workspace without scanning the entire Google account or other workspaces.
- `projects.get` requires a local `projectId` and returns the `project` and model parameters allowed by its account tier. Optional `flowProjectId` (null or UUID) is diagnostic only; the UUID must match the saved binding and does not affect routing.
- `projects.create` also requires `projectId`, `operationId`, and `name` (1-128 characters). Optional `preferredModel` is one of the seven base media models, defaulting to `gflow-nano-banana-2-lite`. After selecting an account, it immediately calls the Google Flow project creation RPC without generating media.

Successful responses use standard chat completions; parse the JSON in `choices[0].message.content`:

```json
{
  "version": 1,
  "instanceId": "Persistent service UUID",
  "workspaceId": "Client workspace UUID",
  "projectBinding": true,
  "capabilities": {"projectBinding": true},
  "project": {
    "id": "Local CutFlow project UUID",
    "name": "Project name",
    "flowProjectId": "Google Flow project UUID",
    "state": "ready",
    "accountLabel": "a***@example.invalid",
    "instanceId": "Persistent service UUID"
  },
  "models": [{
    "id": "gflow-nano-banana-2-lite",
    "kind": "image",
    "maxReferences": 3,
    "aspects": ["1:1", "16:9", "9:16", "4:3", "3:4"],
    "imageSizes": ["1K"],
    "durations": []
  }]
}
```

Control protocol validation, project lookup, and binding conflict errors still return standard chat completions, with content JSON `{version:1,projectBinding:true,error:{code,message,status_code}}`. Clients must check error before validating instance fields in successful responses. This supports the current host ABI, which maps executor exceptions to plugin_error. Transport interruptions remain HTTP/host errors and must not trigger automatic project recreation.

list uses a `projects` array; create/get use one `project`. Project state is `creating|ready|failed|creation_unknown`; failures can include `error:{code,message}`. Responses never expose Cookies, keys, internal account IDs, or raw email addresses. 2K requires Pro and 4K requires Ult; the parameter catalog reflects the known account tier, while actual generation still requires platform verification and credits.

Generation within a project still uses the original media models. Include all of these fields at the top level of the standard request:

```json
{
  "gflow_workspace_id": "Client workspace UUID",
  "gflow_project_id": "Actual Google Flow project UUID",
  "gflow_instance_id": "Persistent service UUID"
}
```

`gflow_project_id` is `flowProjectId`, not the local project ID. All three fields must be present and match the service record. Requests fail if the project account is disabled, removed, changes identity, has an insufficient tier, or lacks a verification route. Switching accounts, falling back to the project pool, and creating replacement projects are prohibited. This rule applies to images, videos, streaming, and non-streaming; request context is cleared after errors and cancellation. When account refresh returns a new object, enabled status and tier are rechecked. Fixed requests always run a nonblocking concurrency precheck without reserving an extra upstream slot. Google Flow responses determine whether credits are sufficient; platform credit errors do not trigger account switching. For successive edits, the client explicitly supplies the selected image as a reference; project binding does not automatically use other session history as references.

Within a workspace, operationId and project request content are persistently idempotent. Identical repeated requests return the original record; conflicting parameters are rejected. Timeouts, cancellation, or lost acknowledgments after RPC startup set creation_unknown, without automatic recreation, to avoid duplicate cloud projects. Service restart changes unfinished creating records to creation_unknown. Confirmed failures also do not retry automatically; users must verify them before creating a new project. Cloud renaming, deletion, migration, and scan-based recovery are outside protocol v1.

SQLite adds metadata and CutFlow project tables to the original flow.db. Existing projects records default to purpose pool; new dedicated projects use cutflow. Rotating clients can see only pool projects. The 27 pinned upstream source files and Google RPC implementations retain their original hashes.

Permission boundaries: An ordinary API Key grants generation access to this EasyCPA instance. Workspace UUIDs group data; they are not additional user authentication and do not provide secure tenant isolation. Existing /v0/management routes still require separate management authentication. Actual host routing, real-account creation, and actual media generation require separate acceptance checks; offline tests do not verify them.
