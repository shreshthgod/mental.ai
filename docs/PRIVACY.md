# Data flow

Local analysis applies limited English safety rules. Trained browser classifiers are unavailable. There is no automatic server fallback, score synchronization, embedding upload or conversation upload in this path.

Authentication still uses network requests. Email/password credentials and session tokens reach the configured authentication service; Google sign-in uses the provider's redirect flow when configured. Configuration, service health and authenticated account-history requests also use the network. This is not a zero-network or fully offline application.

Legacy server mode requires a separate checkbox before submitting text. It sends the submitted text to `/predict` with the session bearer token. The server runs the packaged baseline and can store raw text, cleaned text, lemmatized text, derived scores and the assessment snapshot in the account's database records. Server history is separate from browser history; clearing local data does not delete server records. The authenticated `DELETE /screenings` API deletes the current account's server history, but the current screen does not expose that operation.

Saving check-in answers, saving local screening text/results and remembering themes are separate opt-in choices. Personalization is disabled by default; previously implicit preferences require fresh consent. Themes are coarse keyword categories, not clinical findings or evidence of current danger. Disable clears remembered themes; clear personalization removes the account's preferences. The workspace also offers deletion of its local check-in, history and personalization records.

Browser records are scoped by verified account ID and are not encrypted. They can remain after logout and are available to that account on this browser until deleted. Account scoping prevents ordinary UI crossover; it does not protect against someone with access to browser storage, malicious same-origin scripts or a compromised device. Local history retains at most 12 results. Authentication persistence follows the separate Remember me choice.

No analytics or external error-reporting integration was found in the reviewed frontend data paths. Backend logging uses request IDs/status/error types in the reviewed prediction and persistence paths. This source audit does not cover hosting-provider logs or infrastructure configuration.

`web/scripts/privateqa.mjs` blocks network APIs during local inference. `reviewqa.mjs` inspects browser requests, and `workspaceqa.mjs` submits private text through the rendered workspace against a synthetic API, checks local-save and personalization choices, switches accounts with a mounted check-in, and checks logout. These tests do not establish deployment-wide security or clinical validity.
