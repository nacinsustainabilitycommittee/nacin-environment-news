# NACIN Environment News — Deployable prototype

Open-source wildlife-smuggling news monitoring website with **daily collection** and **manual editorial approval**. No live deployment is implied by this download. Official NACIN/CBIC branding requires permission.

## Architecture

- **Discovery:** GitHub Actions runs Python daily at **03:17 UTC / 08:47 IST** (GitHub may delay or occasionally drop schedules). Collector calls the keyless **GDELT DOC 2.0 API**, asks for 3-day rolling coverage, deduplicates articles by canonical URL, and queues *metadata only* in `site/data/pending.json`.
- **Review:** A repository collaborator with workflow permission triggers **Editorial review (manual)** in Actions, providing a candidate's 16-character `id`, decision `approve` or `reject`, and optional note. Workflow commits the reviewed result to published or rejected. Approval is NOT based merely on matching keywords.
- **Public website:** Only `site/data/published.json` is copied to the GitHub Pages artifact; pending items, rejected articles and internal audit are excluded. Website is HTML/CSS/JS and reads approved JSON.

### Deployment steps

1. Create a GitHub repository; push the **contents of this folder** to its `main` branch. Configure GitHub Pages under **Settings → Pages → Build and deployment → Source: GitHub Actions**.
2. Under **Settings → Actions → General**, allow workflow actions and set workflow `GITHUB_TOKEN` permissions to read/write if repository policy requires it. A branch rule blocking workflow pushes would require a separate pull-request workflow instead. Give editorial access only to trusted collaborators.
3. In **Settings → Environments**, create `editorial`. Set required reviewers if your GitHub account/organization plan supports them. Configure repository access and workflow permissions to ensure only authorized personnel can execute manual review runs. **An environment's required reviewers are an optional additional control, not the only authentication.**
4. Trigger **Actions → Collect wildlife news (daily) → Run workflow** once. It will populate `site/data/pending.json`; open this file and examine candidates, original URLs and source credibility. GitHub may return errors/rate limits: inspect the workflow log and `last_run.json`.
5. Trigger **Actions → Editorial review (manual) → Run workflow**, supply an exact candidate `id`, approve or reject, and add a note. Approved items will be deployed on the next Pages workflow run. You can also run **Deploy public website** manually.
6. Access the URL displayed in the GitHub Pages deployment job. The site shows only explicitly approved reports.

**Important hosting privacy note:** In a public GitHub repository, `pending.json`, audit files, workflow logs and history are still publicly accessible through GitHub, even though Pages excludes them. This design does not contain any sensitive case information and should only process already-public metadata. For a truly confidential editorial queue, use a **private backend/repository with appropriately licensed hosting and access controls**, rather than a public GitHub repository. GitHub Pages availability for private repositories depends on plan and organization settings.

### Local setup

Requires Python 3.11+; no Python packages to install.

```bash
python scripts/collector.py                # needs internet
python scripts/review.py STORY_ID approve --editor "Editor name" --note "Verified original source"
python scripts/build_public.py
cd site/public && python -m http.server 8000
```

Open http://localhost:8000. Test offline with `python -m unittest discover -s tests -v`.

### Editorial protocol

1. Verify source link and original reporting date (GDELT "seen" date may differ from publication date).
2. Verify whether enforcement figures/species/locations are reported, not independently verified; avoid drawing unsupported trafficking route conclusions.
3. Check duplicate stories, corrections, arrests vs convictions, protected-species status, and where relevant CITES listings by date.
4. Approve only useful reports; use reject for irrelevant, misleading or unverifiable pieces. Do not include operational intelligence, names of private persons beyond what is necessary, or non-public information.
5. The website provides **headlines and links** rather than copying article text or images. Before adding snippets or photography, check reuse licenses and attribution requirements.

### Limitations / future enhancements

- Keyword screening is a candidate filter, not reliable AI classification. Multilingual incidents may be missed and false positives will need review.
- No verified live results are packaged: initial approved stories are empty. Live collection starts only after hosting and enabling workflows.
- GitHub Action schedule is not a guaranteed clock. GDELT queries can change, rate-limit or become temporarily unavailable. Logs report failures; consider retry/alert support for production operations.
- Concurrent workflow write conflicts can occasionally happen; workflow concurrency reduces overlap but does not replace a database transaction. For multiple editors or significant traffic, migrate to Postgres/SQLite plus authenticated moderation dashboard.
- To restrict news by jurisdiction, add editorial metadata after verifying source articles. Avoid treating media attention as a representative sample of actual wildlife trafficking.

## References

- GDELT DOC API: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
- GitHub scheduled workflows: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
- GitHub schedule caveats: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows

## Reader-submitted links (new)

- The public homepage's **Submit News Link** button opens a GitHub Issue Form in this repository (requires GitHub login). The form collects headline, URL, category and optional public-context notes. **Enable GitHub Issues** in repository Settings. Create a `news-submission` label (the label definition is in `.github/labels.yml`; GitHub does not automatically import this file).
- New issues **do not automatically enter the review queue**. An editor first checks for spam, malicious content, irrelevant reports or sensitive information and triggers **Actions → Import submitted news link (editor triage)** using the issue number. Imported links enter `site/data/pending.json` (not the public website). If the label does not match or mandatory fields are invalid, import fails.
- The editor then uses the existing **Editorial review (manual)** workflow with the printed 16-character ID to approve or reject. Until approved, nothing appears on the public site. Both manually imported and automatically discovered articles follow the same approval process.
- Repository issues, candidates and any submission notes are **public in a public repository**. Tell contributors not to enter confidential information. For internal-only submissions, a private authenticated form and backend are necessary.
- If copying files to another repository, run the **Deploy public website** workflow again: `config.json` is generated with the correct GitHub repository name and submission buttons then work. When opening `index.html` as a local file, links remain placeholders until built/deployed.
