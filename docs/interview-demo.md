# Controlled interview demo

This mode exposes the local Streamlit UI through a temporary Cloudflare Quick Tunnel. FastAPI, Qdrant, models, private labels, and review data remain on the interviewer's machine. It is not a permanent cloud deployment.

## Security and cost boundaries

- Docker publishes the UI and API only on `127.0.0.1`.
- The tunnel connects to the UI over the private Compose network; the API is not tunneled.
- `ALADDIN_DEMO_PASSWORD` protects the Streamlit session.
- `ALADDIN_API_TOKEN` protects every `/api/v1/*` call between UI and API.
- `ALADDIN_RATE_LIMIT_PER_MINUTE` limits API traffic per client address.
- `ALADDIN_MAX_GENERATIONS_PER_DAY` places a hard in-process ceiling on analysis requests that could call Gemini.
- Quick Tunnel URLs are temporary, random, and unsuitable for permanent hosting or an uptime claim.

The in-memory limits target a single-process interview demo. A multi-instance production deployment requires a shared limiter and budget store such as Redis or a managed API gateway.

## Preparation

1. Install and start Docker Desktop.
2. Copy `.env.example` to `.env` and set the Gemini configuration.
3. On the first `make demo-up`, enter a demo password of at least 12 characters when prompted. The setup script stores it with restricted file permissions and generates a separate internal API token without displaying it.
4. To configure the values before building, run `python3 scripts/configure_interview_demo.py`.
5. Keep `ALADDIN_MAX_GENERATIONS_PER_DAY` low enough for the planned interview, for example 30–50.
6. Confirm that the private Qdrant index and topic-label file exist locally.

Never commit `.env`, the raw reviews, private labels, or Qdrant storage.

## Start and stop

```bash
make demo-up
```

The command builds the images, waits for API/UI health checks, starts the Quick Tunnel, and follows its logs. Copy only the displayed `https://...trycloudflare.com` URL. Do not share the local API URL, `.env`, or terminal output containing other information.

After the interview:

```bash
make demo-down
```

Verify that the temporary URL no longer loads.

## External-network acceptance test

Perform this once before relying on the demo:

1. Disconnect the test phone from Wi-Fi and use its mobile network.
2. Open the temporary URL in a private browser window.
3. Confirm the password gate appears and rejects an incorrect password.
4. Sign in and run one Japanese market-comparison question.
5. Confirm the task, inferred markets, low-rating filter, tool trace, statistics, and evidence cards.
6. Refresh the page and confirm no API key or internal API URL is displayed.
7. Run `make demo-down` and confirm the public URL stops responding.

## Interview-day checklist

- Connect the Mac to power and disable sleep for the interview duration.
- Start and warm the demo 30 minutes before the call.
- Test one English and one Japanese question.
- Keep the local recording GIF available as a fallback.
- Share the URL and demo password privately with the interviewer only.
- Watch request volume and stop the tunnel immediately after the session.
