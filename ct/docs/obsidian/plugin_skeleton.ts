/*
  CT Obsidian Companion — Plugin Skeleton (commented, conceptual)
  - This file is intentionally non-functional sample code showing how a read-only
    viewer plugin could interact with Obsidian's SecretStorage and fetch
    CT runtime status via the Gateway.
  - DO NOT ENABLE THIS as runtime code. This is a design artifact only.
*/

// import { Plugin } from 'obsidian'

// export default class CtViewerPlugin extends Plugin {
//   async onload() {
//     // Conceptual: request token from SecretStorage (new API)
//     // const token = await this.app.secretStorage.get('ct.viewer.token')
//     // if (!token) return
//     // Perform a read-only fetch to the gateway
//     // const resp = await fetch(`${this.settings.gatewayUrl}/governance/orchestrator-state`, {
//     //   headers: { 'Authorization': `Bearer ${token}` }
//     // })
//     // const state = await resp.json()
//     // Render state in a read-only view or pane
//   }
//
//   onunload() {
//     // Clean up UI elements; do not persist any secrets
//   }
// }

/*
  Security notes (inline):
  - Never write the token to a note or to local plugin settings saved in plaintext.
  - Prefer short-lived tokens; use SecretStorage for storage and retrieval.
  - The plugin must validate server TLS and treat a missing or invalid token as 'no data'.
*/
