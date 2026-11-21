# Deploy the public demo on Vercel

The Vercel deployment runs the **hosted, synthetic-only profile**: invented people only, no file uploads, secure cookies. Never connect real ASD data to it.

## How it works

- `app.py` exposes the cockpit as a WSGI app. Vercel detects it and runs the whole cockpit as one Python function (`.python-version` pins Python 3.13).
- Vercel has no persistent disk. Each function instance builds the two demo months in `/tmp` on its first request, which takes about 10 seconds. `vercel.json` allows up to 60 seconds.
- Sessions are signed with `COCKPIT_SESSION_SECRET`, so a sign-in stays valid when Vercel serves the next request from another instance.
- The demo account is created on each instance from environment variables. No password is stored in the repository.
- There are no Python dependencies; `requirements.txt` is intentionally empty.

## Steps

1. Push the repository to GitHub.
2. At [vercel.com](https://vercel.com), choose **Add New… → Project** and import `hmnhoomandev/Integration-Cockpit`. Keep the framework preset **Other** and leave the build settings empty.
3. Under **Environment Variables**, add the following, all for Production:

   | Name | Value |
   | --- | --- |
   | `COCKPIT_DEMO_USER` | the jury username, for example `bern-jury` |
   | `COCKPIT_DEMO_PASSWORD` | a password of 12 or more characters |
   | `COCKPIT_SESSION_SECRET` | the output of `python3 -c "import secrets;print(secrets.token_urlsafe(48))"` |

4. Click **Deploy**. Open `https://<project>.vercel.app/login`. The first page load can take about 10 seconds while the instance builds the demo data.
5. Share the username and password only through the organisers’ private channel.

If the page says “Set COCKPIT_DEMO_USER …”, a variable is missing or too short. Add it and redeploy.

## Known limits of the serverless demo

- When Vercel starts a new instance, the selected report date and the demo role switch back to their defaults (the latest month, and the demo account). The sign-in itself stays valid.
- Intake PDFs are read with a built-in reader that handles the bundled sample; OCR for scanned documents is not available on Vercel.
- The Claude analysis stays off. The AI forecast and the privacy shield run inside the function as usual.
- For the full experience, including persistent state, use the local app or the Docker/Infomaniak setup in [DEPLOY-INFOMANIAK.fa.md](DEPLOY-INFOMANIAK.fa.md).
