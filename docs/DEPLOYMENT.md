# Deployment

The temporary judge URL uses this laptop’s loopback-only synthetic instance behind Cloudflare HTTPS. It remains available while the laptop, local application and tunnel are running. The local credential file is excluded from Git and belongs in a private delivery channel. Avoid entering any production data.

For a public demo on a VPS, `deploy/compose.yml` runs the image behind Caddy with automatic HTTPS and a persistent volume; set `DOMAIN` in `deploy/.env`, create an account with `docker compose run --rm cockpit account <name> judge`, then `docker compose up -d --build`. The compose file sets `COCKPIT_BEHIND_PROXY=1`, so the sign-in limit counts the client address appended by Caddy instead of the proxy's own. Never set it when the app port is reachable directly. A step-by-step guide in Persian for Infomaniak is in [DEPLOY-INFOMANIAK.fa.md](DEPLOY-INFOMANIAK.fa.md).

For a managed deployment, build the included Dockerfile and mount a writable private volume at the path used by `COCKPIT_DB`. Create a judge account by running the image with the `account` command and the same volume. The password is entered interactively or provided with a host-managed secret through `COCKPIT_PASSWORD`. The service must sit behind HTTPS. Allow health checks at `/health`, and verify signed-out denial, upload denial, login, locale changes, snapshot switching and exports after launch. Use one replica while sessions and snapshots remain on SQLite. Restrict access to the underlying port and provision backups where appropriate.

A managed container was not launched in the supplied Google Cloud projects. Cloud Run was disabled in the default project and billing was disabled in each of the four accessible projects. The activated judge-facing fallback is the temporary tunnel. Sites hosting expects a static build or Cloudflare Worker ES module; the verified Python server uses a separate HTTPS reverse proxy.

## Rehearsal and offline fallback

Download the [offline demo bundle](https://github.com/hmnhoomandev/Integration-Cockpit/releases/download/v1.0.0/integration-cockpit-offline-v1.0.0.zip), extract it, and run `python3 -m cockpit.server serve --demo` from its project directory. Python 3.12 or later is required. Open http://127.0.0.1:8000 and use the newly generated local credential printed on first start. The bundle contains source, the narrated video, captions, a sample results workbook, and all 22 generated source workbooks. The app generates its own synthetic snapshots on first start. Keep the narrated video open separately for fallback playback.

To rehearse the published link from another device, run the deployment smoke test from the source directory. It prompts for the password without echoing it, uses its own sign-in session, replays both synthetic months, verifies the exported A1 evidence, and signs out.

```sh
python3 -m cockpit.smoke https://listening-brian-served-upcoming.trycloudflare.com bern-jury
```

## Revoke copied sessions on a restored instance

Before exposing a restored database, explicitly invalidate the sessions copied from the backup. The command targets the configured database, so specify the restored path.

```sh
python3 -m cockpit.server --db /private/restored-cockpit.sqlite revoke-sessions
```

Use fresh authentication to verify both monthly snapshots and the latest Excel report. Keep the restore isolated until the acceptance checks pass.
