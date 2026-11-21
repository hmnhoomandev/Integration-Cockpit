# Deployment

The temporary judge URL uses this laptop’s loopback-only synthetic instance behind Cloudflare HTTPS. It remains available while the laptop, local application and tunnel are running. The local credential file is excluded from Git and belongs in a private delivery channel. Avoid entering any production data.

For a managed deployment, build the included Dockerfile and mount a writable private volume at the path used by `COCKPIT_DB`. Create a judge account by running the image with the `account` command and the same volume. The password is entered interactively or provided with a host-managed secret through `COCKPIT_PASSWORD`. The service must sit behind HTTPS. Allow health checks at `/health`, and verify signed-out denial, upload denial, login, locale changes, snapshot switching and exports after launch. Use one replica while sessions and snapshots remain on SQLite. Restrict access to the underlying port and provision backups where appropriate.

A managed container was not launched in the supplied Google Cloud projects. Cloud Run was disabled in the default project and billing was disabled in each of the four accessible projects. The activated judge-facing fallback is the temporary tunnel. Sites hosting expects a static build or Cloudflare Worker ES module; the verified Python server uses a separate HTTPS reverse proxy.
