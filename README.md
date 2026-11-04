# HOMIE cloud demonstration

This package runs the working FastAPI demo and actual fitted scikit-learn models.
The root page is the transaction workspace. `/research` shows historical evidence;
`/live` performs read-only Solana checks; `/fee-proof` shows recorded local evidence.
It does not sign or submit transactions. The research and exported demo models
remain distinct comparisons, as explained in the interface.

## Deploy on Render

1. Create a Render account and a private GitHub repository for the contents of this
   `homie-demo` directory (Dockerfile and render.yaml must be at repository root).
   Commit the packaged `data` directory too. It contains public historical data
   and fitted models, not private keys. The largest file is about 77 MB.
2. In Render choose New > Blueprint, connect that repository and select its branch.
3. Review the proposed 1 CPU / 2 GB web service and 1 GB persistent disk. This is paid;
   check Render's displayed price before creating the service. The 2 GB selection
   leaves room for pandas, model inference and live-history range checks; 512 MB
   has not been validated for this workload.
4. Deploy. The Docker build installs the pinned model-compatible dependencies.
   It starts one Uvicorn worker, binds `0.0.0.0:$PORT`, and checks `/healthz`.
5. Open the service's HTTPS URL. Enter username `homie` and the generated
   `HOMIE_DEMO_PASSWORD` shown in Render's environment settings. Share this demo
   password only with the intended evaluators; do not commit it to Git.
6. Run a historical example, reveal its result, and open Research evidence.
   For live scoring, open `/live` and refresh history for the desired network.

The username/password protect the whole app, including API calls and saved
observations. This is a shared evaluator login, not a multi-user account system.
All logged-in evaluators share the observation list. Keep the host HTTPS-only.

## Stored data

Models and historical data live in the image. New observations and live snapshots
are written under `/var/data/homie`, on the persistent disk. Do not mount a disk
on `/app/data`: it would hide the packaged model files. Use one worker/instance
because the refresh-job registry is in memory and the study store uses SQLite.
No existing local study database, live snapshots, credentials, wallet keys, reports
in Word/PDF, or raw research downloads are included in this package.

Public Solana RPC can rate-limit or fail. The historical demo works without RPC;
live checks report missing data rather than inventing results. Refreshes may take
several minutes. Missing or stale history withholds live scores.

## Local Docker verification

Create a local, untracked `.env` containing:

    HOMIE_DEMO_USER=homie
    HOMIE_DEMO_PASSWORD=<choose-a-password-at-least-16-characters>

Run:

    docker build -t homie-demo .
    docker run --rm --env-file .env -p 10000:10000 -v homie-state:/var/data homie-demo

Open http://localhost:10000. Health endpoint: http://localhost:10000/healthz.
The startup check loads the model and historical inputs; missing artifacts fail
startup. This package must only load its own trusted joblib model, never uploads.

## Rebuild from the research checkout

    .venv/bin/python deploy/build_package.py

Upload the generated directory, not the whole research repository. The bundle
contains a manifest of source/data SHA-256 hashes. Inference does not retrain models.

Provider documentation: https://render.com/docs/docker and https://render.com/docs/disks
