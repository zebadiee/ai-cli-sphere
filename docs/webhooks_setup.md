# Webhooks Setup Guide

This guide outlines how to set up webhooks for GitHub Actions to integrate with the Om Console.

## GitHub Webhook Configuration

1.  **Navigate to your GitHub Repository:** Go to `Settings > Webhooks`.
2.  **Add Webhook:** Click on `Add webhook`.
3.  **Payload URL:** Enter the URL for your Om Console webhook endpoint (e.g., `https://console.omarchy.com/webhooks/github`).
4.  **Content type:** Select `application/json`.
5.  **Secret:** (Optional) Provide a secret token for security. This should be stored securely in your Om Console configuration.
6.  **Which events would you like to trigger this webhook?** Select `Just the push event` or customize as needed.
7.  **Active:** Ensure `Active` is checked.
8.  **Add webhook:** Click `Add webhook`.

## Om Console Configuration

Refer to the Om Console documentation for specific steps on how to configure the incoming GitHub webhook to process events and trigger actions within the Om Console.
