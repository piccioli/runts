# PRD: DevOps — Healthcheck, Pre-commit, Release, Dev Container, CI/CD, Ambienti

## Introduction

Il progetto manca di infrastruttura DevOps di base: nessuna pipeline CI/CD, nessun linting automatico, nessun versionamento formale, nessun devcontainer. Questa release aggiunge tutto il necessario per un ciclo di sviluppo professionale: healthcheck Docker, hook pre-commit con ruff/black/mypy, script di bump versione, dev container VS Code, GitHub Actions CI/CD con push su ghcr.io, e deploy automatico su due VPS Hetzner (UAT + prod) via SSH.

**Infrastruttura:**
- Registry: GitHub Container Registry (`ghcr.io/<owner>/runts`)
- UAT: VPS Hetzner dedicato, deploy automatico su merge in `develop`
- Prod: VPS Hetzner dedicato, deploy automatico su merge in `prod`
- Deploy: SSH + `docker compose pull && docker compose up -d`

**Pre-commit attuale:** hook shell custom in `.git/hooks/pre-commit` (solo pytest). Non tracciato da git. Da migrare al framework `pre-commit`.

---

## Goals

- Rilevare errori di linting/type il prima possibile (pre-commit locale)
- Build e test automatici ad ogni push via GitHub Actions
- Immagine Docker pubblicata su ghcr.io ad ogni merge su `develop` o `prod`
- Deploy zero-touch su UAT e prod via SSH
- Versione del progetto tracciata con semver a partire da `0.1.0`
- Dev container riproducibile per onboarding rapido

---

## User Stories

### US-001: Endpoint `/health` per Docker healthcheck
**Description:** As an operator, I want a `/health` endpoint so that Docker and load balancers can verify the app is running correctly.

**Acceptance Criteria:**
- [ ] Aggiungere route `GET /health` in `web/app.py` che esegue `SELECT COUNT(*) FROM enti` sul DB
- [ ] Risponde `200 {"status": "ok", "enti": N}` se il DB è raggiungibile e `N > 0`
- [ ] Risponde `503 {"status": "error", "detail": "..."}` se il DB non è raggiungibile o `N == 0`
- [ ] Aggiungere a `docker-compose.yml`: `healthcheck: test: ["CMD", "curl", "-f", "http://localhost:8000/health"], interval: 30s, timeout: 5s, retries: 3`
- [ ] Typecheck passes
- [ ] Verify in browser: `GET /health` risponde 200 con JSON

### US-002: Migrazione a framework `pre-commit` con ruff, black, mypy
**Description:** As a developer, I want automated linting and type checks on every commit so that code quality issues are caught before they reach the repo.

**Acceptance Criteria:**
- [ ] Aggiungere `pre-commit` a `scraper/requirements.txt` (o `requirements-dev.txt` nuovo)
- [ ] Creare `.pre-commit-config.yaml` nella root con hooks: `ruff` (linting), `ruff-format` (formatting), `mypy` (type check su `scraper/` e `web/`), hook locale per `pytest scraper/test_*.py`
- [ ] Il vecchio `.git/hooks/pre-commit` viene rimpiazzato da `pre-commit install` (documentato nel README o in uno script di setup)
- [ ] Aggiungere `.pre-commit-config.yaml` al repo (file tracciato da git)
- [ ] `pre-commit run --all-files` passa senza errori sul codebase attuale (fixare eventuali warning ruff/mypy prima di committare)
- [ ] Typecheck passes

### US-003: File `VERSION` e script `scripts/bump-version.sh`
**Description:** As a developer, I want a version bump script so that I can release new versions with a single command and get a consistent CHANGELOG.

**Acceptance Criteria:**
- [ ] Creare file `VERSION` nella root con contenuto `0.1.0`
- [ ] Creare `scripts/bump-version.sh` che accetta un argomento: `major`, `minor`, o `patch`
- [ ] Lo script: legge la versione corrente da `VERSION`, incrementa il componente richiesto, aggiorna `VERSION`, crea una sezione in `CHANGELOG.md` con la data e un placeholder per le note, crea un git tag `v<nuova_versione>` e fa `git commit -m "chore: bump version to v<nuova_versione>"`
- [ ] Creare `CHANGELOG.md` con sezione iniziale `## [0.1.0] - 2026-06-02` e note "Prima release di sviluppo"
- [ ] Eseguire `bash scripts/bump-version.sh patch` → `VERSION` diventa `0.1.1`, tag `v0.1.1` creato
- [ ] Typecheck passes (script bash, nessun typecheck rilevante)

### US-004: Dev container VS Code (`.devcontainer/`)
**Description:** As a developer, I want a dev container configuration so that I can start coding in a reproducible environment without manual setup.

**Acceptance Criteria:**
- [ ] Creare `.devcontainer/devcontainer.json` con: immagine base `python:3.12`, `postCreateCommand` che installa `scraper/requirements.txt`, `web/requirements.txt` e `pre-commit install`, estensioni VS Code consigliate: `ms-python.python`, `charliermarsh.ruff`, `ms-python.mypy-type-stubs`
- [ ] Creare `.devcontainer/Dockerfile` (o usare immagine diretta) che include Playwright e i browser Chromium necessari allo scraper
- [ ] Il dev container monta la directory del progetto come workspace
- [ ] Documentare nel README che il dev container è disponibile
- [ ] Typecheck passes

### US-005: GitHub Actions — CI pipeline (lint + test + build)
**Description:** As a developer, I want a CI pipeline that runs on every push so that broken code is caught before merge.

**Acceptance Criteria:**
- [ ] Creare `.github/workflows/ci.yml` che si attiva su `push` e `pull_request` verso qualsiasi branch
- [ ] Job `lint-test`: checkout, setup Python 3.12, installa requirements, esegue `pre-commit run --all-files`, poi `pytest scraper/test_*.py -v`
- [ ] Job `build`: checkout, `docker build -t runts:test .`, verifica che l'immagine parta con `docker run --rm runts:test python -c "import uvicorn"`
- [ ] I job sono indipendenti e girano in parallelo
- [ ] Il workflow usa `ubuntu-latest`
- [ ] Typecheck passes

### US-006: GitHub Actions — build e push immagine su ghcr.io
**Description:** As a developer, I want the Docker image pushed to GitHub Container Registry on every merge to develop or prod so that the target servers can pull it.

**Acceptance Criteria:**
- [ ] Creare `.github/workflows/publish.yml` che si attiva su `push` su branch `develop` e `prod`
- [ ] Login su `ghcr.io` con `GITHUB_TOKEN` (nessun secret aggiuntivo)
- [ ] Build e push dell'immagine con tag: `ghcr.io/<owner>/runts:develop` per il branch develop, `ghcr.io/<owner>/runts:latest` e `ghcr.io/<owner>/runts:v<VERSION>` per il branch prod (legge `VERSION` dal file)
- [ ] Usa `docker/build-push-action@v5` con cache layer (`cache-from: type=gha`, `cache-to: type=gha,mode=max`)
- [ ] Typecheck passes

### US-007: GitHub Actions — deploy automatico su UAT (Hetzner)
**Description:** As a developer, I want the UAT server to automatically update when I merge to develop so that testers always have the latest code.

**Acceptance Criteria:**
- [ ] Creare `.github/workflows/deploy-uat.yml` che si attiva al completamento riuscito di `publish.yml` sul branch `develop`
- [ ] Usa `appleboy/ssh-action` per connettersi al VPS UAT tramite i secret GitHub: `UAT_SSH_HOST`, `UAT_SSH_USER`, `UAT_SSH_KEY`
- [ ] Il comando remoto eseguito: `cd /opt/runts && docker compose pull && docker compose up -d && docker image prune -f`
- [ ] In caso di fallimento SSH, il workflow fallisce con un messaggio chiaro
- [ ] Documentare nel README i secret da configurare in GitHub
- [ ] Typecheck passes

### US-008: GitHub Actions — deploy automatico su prod (Hetzner)
**Description:** As a developer, I want the production server to automatically update when I merge to prod so that releases are zero-touch.

**Acceptance Criteria:**
- [ ] Creare `.github/workflows/deploy-prod.yml` che si attiva al completamento riuscito di `publish.yml` sul branch `prod`
- [ ] Usa `appleboy/ssh-action` con secret distinti: `PROD_SSH_HOST`, `PROD_SSH_USER`, `PROD_SSH_KEY`
- [ ] Il comando remoto eseguito: `cd /opt/runts && docker compose pull && docker compose up -d && docker image prune -f`
- [ ] Typecheck passes

### US-009: docker-compose.yml multi-ambiente
**Description:** As a developer, I want separate Docker Compose configurations for local, UAT, and prod so that each environment has the right settings.

**Acceptance Criteria:**
- [ ] Rinominare l'attuale `docker-compose.yml` in `docker-compose.base.yml` (o tenerlo come base)
- [ ] Creare `docker-compose.override.yml` per lo sviluppo locale: porta `8000:8000`, volume `./runts.db`, `./attachments`
- [ ] Creare `docker-compose.uat.yml`: usa immagine `ghcr.io/<owner>/runts:develop`, porta `8000:8000`, volumi su path del server UAT, variabile `ENV=uat`
- [ ] Creare `docker-compose.prod.yml`: usa immagine `ghcr.io/<owner>/runts:latest`, porta `8000:8000`, volumi su path del server prod, variabile `ENV=prod`, `restart: always`
- [ ] Aggiornare il README con istruzioni: locale (`docker compose up`), UAT/prod (`docker compose -f docker-compose.prod.yml up -d`)
- [ ] Typecheck passes

---

## Functional Requirements

- FR-1: `GET /health` risponde 200/503 con JSON `{status, enti}`
- FR-2: `docker-compose.yml` ha `healthcheck` che chiama `/health`
- FR-3: `.pre-commit-config.yaml` tracciato in git con ruff, ruff-format, mypy, pytest
- FR-4: `VERSION` contiene la versione semver corrente (`0.1.0` iniziale)
- FR-5: `scripts/bump-version.sh [major|minor|patch]` aggiorna VERSION, CHANGELOG e crea git tag
- FR-6: `.devcontainer/devcontainer.json` con Python 3.12 + Playwright + pre-commit
- FR-7: `.github/workflows/ci.yml` — lint+test+build su ogni push/PR
- FR-8: `.github/workflows/publish.yml` — push immagine ghcr.io su develop e prod
- FR-9: `.github/workflows/deploy-uat.yml` — SSH deploy su UAT dopo publish develop
- FR-10: `.github/workflows/deploy-prod.yml` — SSH deploy su prod dopo publish prod
- FR-11: File docker-compose separati per local / UAT / prod

---

## Non-Goals

- Nessun rollback automatico in caso di deploy fallito
- Nessun monitoring/alerting (Prometheus, Grafana)
- Nessun secret management avanzato (Vault, AWS SSM)
- Nessuna gestione di database migrations automatiche nel deploy
- Il branch `develop` e `prod` non vengono creati da questa release — da fare manualmente prima

---

## Technical Considerations

- **ghcr.io**: il repo GitHub deve essere pubblico O il package deve essere reso pubblico manualmente dopo il primo push. In alternativa usare `packages: write` nei permissions del workflow.
- **pre-commit**: dopo `pre-commit install`, il file `.git/hooks/pre-commit` viene sovrascritto dal framework. Il vecchio hook pytest viene replicato come local hook in `.pre-commit-config.yaml`.
- **Playwright nel devcontainer**: richiede `playwright install chromium --with-deps` nel `postCreateCommand` (circa 300MB extra).
- **VPS Hetzner**: assumiamo che Docker e Docker Compose siano già installati. Il path `/opt/runts` deve contenere il `docker-compose.prod.yml` e un file `.env` con le variabili d'ambiente sensibili.
- **Secret GitHub da configurare**: `UAT_SSH_HOST`, `UAT_SSH_USER`, `UAT_SSH_KEY`, `PROD_SSH_HOST`, `PROD_SSH_USER`, `PROD_SSH_KEY`

---

## Success Metrics

- `pre-commit run --all-files` passa senza errori
- La CI GitHub Actions è verde su ogni PR
- Il deploy UAT avviene automaticamente entro 3 minuti dal merge su `develop`
- `bash scripts/bump-version.sh minor` crea correttamente tag e aggiorna CHANGELOG

---

## Open Questions

- Il repo GitHub è già pubblico? (influisce sulla visibilità delle immagini ghcr.io)
- I VPS Hetzner hanno già Docker installato, o serve uno script di provisioning?
- Il `docker-compose.yml` su UAT/prod deve includere anche lo scraper schedulato, o solo la web app?
