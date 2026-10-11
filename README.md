# Research & Action Brief

A consulting dashboard for the LangChain Multi-Agent Learner Activity. Enter a business question to run **Search → Researcher → Analysis → Operational Actions** and download an evidence-informed Markdown brief.

## Run locally

Use Python 3.10 or later (3.10 is the locally tested version).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Enter your keys in `.streamlit/secrets.toml`, then run:

```bash
streamlit run app.py
```

Do not overwrite an existing secrets file containing your keys. You may instead set `GEMINI_API_KEY` and `SERP_API_KEY` as environment variables. Environment values take precedence. Optional `GEMINI_MODEL` defaults to `gemini-3.5-flash`; change it if your account uses another supported Gemini model. Keep secrets out of Git.

## Publish on Streamlit Community Cloud

1. Create a GitHub repository and upload `app.py`, `MAS_LangChain.py`, `requirements.txt`, `README.md`, `.gitignore`, and the `.streamlit` folder **excluding secrets.toml**. The provided `research-action-brief.zip` contains only deployable source and tests; unzip it before uploading. `requirements-lock.txt` records the complete tested local environment.
2. Sign in at https://share.streamlit.io and choose **Create app** / **Deploy a public app from GitHub**.
3. Select the repository and branch; set the entrypoint to `app.py`.
4. In **Advanced settings**, select Python 3.10 and add the following secrets with your real keys:

   ```toml
   GEMINI_API_KEY = "your-gemini-key"
   SERP_API_KEY = "your-serpapi-key"
   GEMINI_MODEL = "gemini-3.5-flash"
   ```

5. Deploy, open the resulting `https://….streamlit.app` URL, and generate the example brief. Share that URL with your mentor.

Deployment reference: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy

The owner's cloud keys power all visitors' requests. Each successful run normally uses one SerpAPI search and three Gemini calls; retries can add calls. There is no authentication, database or persistent report history. Streamlit session state keeps only the current browser session's latest successful result.

## Backend and classroom walkthrough

`MAS_LangChain.py` exposes `run_workflow(request: str) -> str`, returning Markdown. It raises a user-safe `WorkflowError` on invalid input, missing credentials, search errors or model failures.

- **Search:** fetch up to eight Google organic results through SerpAPI, retaining titles, snippets and original URLs.
- **Researcher:** a LangChain prompt/model/parser chain summarizes evidence and gaps.
- **Analysis:** a second chain identifies implications, opportunities, risks and missing information.
- **Operational Actions:** a third chain returns a validated Pydantic response, rendered into the four required sections and an original-source list.

These are three sequential prompt-based agents, matching the activity; they do not independently browse or use autonomous tool loops. The final stage is instructed to return exactly three offerings for the example question. Factual grounding and recommendation quality still require human review. The app reads snippets, not full reports, and does not verify claims within those pages.

## Validation

```bash
python -m unittest discover -s tests -v
```

Tests use mocked search/model responses and Streamlit's AppTest; they do not spend API credits. Live acceptance: run the example and a second business question, check all four sections and source links, verify three offerings for the example, download the brief, and repeat once on the public URL. Live checks require working API keys and quota.
