# Build and Push Pipeline Setup

This document captures every step required to set up the GitHub Actions build-and-push
pipeline for a repo using the centralised `devops-template` repository.

---

## Overview

The pipeline:
- Triggers automatically when code is pushed to `main` (PR merges)
- Can be triggered manually from any branch via the GitHub Actions UI
- Authenticates to Azure using OIDC (no passwords or secrets stored)
- Builds the Docker image and pushes it to Azure Container Registry (ACR)
- Tags the image with both `:latest` and `:<short-git-sha>`

All logic lives in `HammadTariq14/devops-template`. Each code repo contains
only a short caller workflow (~15 lines).

---

## Prerequisites

- Azure `dev-persistent` Terraform stack deployed (provides ACR, managed identity)
- `devops-template` repo pushed to GitHub with templates
- GitHub repo exists and you have admin access
- Terraform installed locally
- `Dockerfile` in the repo root

---

## Step 1 — Create a GitHub Environment

In the GitHub repo UI:

1. Go to repo **Settings** > **Environments**
2. Click **New environment**
3. Name it `dev` > click **Configure environment** > save

> The `environment: dev` on the job makes GitHub always send `environment:dev`
> as the OIDC subject, matching the single federated credential per repo.

---

## Step 2 — Terraform: Managed Identity (one-time, shared)

File: `platform-infra/stack/dev-persistent/07-github-actions.tf`

Already created once. All repos share this identity.

```hcl
module "github_actions_identity" {
  source = "../../modules/user-assigned-identity"
  name                = "${local.resource_prefix}-github-actions"
  resource_group_name = module.resource_group.name
  location            = module.resource_group.location
  tags = local.common_tags
}
```

---

## Step 3 — Terraform: AcrPush Role (one-time, shared)

File: `platform-infra/stack/dev-persistent/07-github-actions.tf`

Already created once. All repos share this role assignment.

```hcl
resource "azurerm_role_assignment" "github_actions_acr_push" {
  scope                = module.container_registry.id
  role_definition_name = "AcrPush"
  principal_id         = module.github_actions_identity.principal_id
}
```

---

## Step 4 — Terraform: Federated Credential (once per repo)

File: `platform-infra/stack/dev-persistent/terraform.tfvars`

Add one entry per repo:

```hcl
github_actions_federated_repos = [
  {
    name    = "<repo-short-name>-env-dev"
    subject = "repo:HammadTariq14/<repo-name>:environment:dev"
  },
]
```

Then run:

```bash
cd platform-infra/stack/dev-persistent
terraform apply
```

---

## Step 5 — Get Output Values

```bash
terraform output github_actions_identity_client_id
terraform output github_actions_identity_tenant_id
```

---

## Step 6 — Set GitHub Repository Secrets

**Settings > Secrets and variables > Actions > New repository secret**

| Secret Name            | Value                                          |
|------------------------|------------------------------------------------|
| `AZURE_CLIENT_ID`      | output from `github_actions_identity_client_id` |
| `AZURE_TENANT_ID`      | output from `github_actions_identity_tenant_id` |
| `AZURE_SUBSCRIPTION_ID`| your Azure subscription ID                     |

**Current values for this project:**

| Secret Name            | Value                                          |
|------------------------|------------------------------------------------|
| `AZURE_CLIENT_ID`      | `1245fb1d-d3b3-41bb-900a-623f25b636d5`         |
| `AZURE_TENANT_ID`      | `58774800-82eb-4017-8fe0-e631bc71d5d7`         |
| `AZURE_SUBSCRIPTION_ID`| `87ce1e2f-4669-4d05-b2c4-93419e46ad76`         |

---

## Step 7 — Create the Caller Workflow

Create `.github/workflows/build-and-push.yaml` in the repo:

```yaml
name: Build and Push to ACR

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  build-and-push:
    uses: HammadTariq14/devops-template/.github/workflows/build-and-push.yaml@v1
    with:
      image_name: your-image-name
    secrets: inherit
```

> Only change per repo: `image_name` value.

### Optional inputs

| Input | Default | Description |
|-------|---------|-------------|
| `image_name` | *(required)* | Image name in ACR |
| `acr_name` | `ampliordevacr` | ACR registry name |
| `dockerfile` | `./Dockerfile` | Path to Dockerfile |
| `context` | `.` | Docker build context |

---

## Step 8 — Commit and Push

```bash
git add .github/workflows/build-and-push.yaml
git commit -m "Add build and push workflow"
git push origin main
```

---

## How to Add a New Repo

Steps 2, 3 are already done (shared resources). For each new repo:

1. Create `dev` environment in GitHub (Step 1)
2. Add one entry to `github_actions_federated_repos` in `terraform.tfvars` (Step 4)
3. Run `terraform apply`
4. Set 3 GitHub secrets (Step 6) — same values for all repos
5. Create the caller workflow with correct `image_name` (Step 7)
6. Commit and push (Step 8)

---

## Trigger Behaviour

| Trigger | Fires? | OIDC Subject |
|---------|--------|--------------|
| PR merged into `main` | Yes | `environment:dev` |
| Push directly to `main` | Yes | `environment:dev` |
| Manual dispatch from `main` | Yes | `environment:dev` |
| Manual dispatch from feature branch | Yes | `environment:dev` |

> All scenarios match the single `environment:dev` federated credential.

---

## Image Tags Produced

| Tag | Example | Purpose |
|-----|---------|---------|
| `:latest` | `hello-world-api:latest` | Always points to newest build |
| `:<short-sha>` | `hello-world-api:a1b2c3d` | Immutable, tied to exact commit |

---

## Template Versioning

The `devops-template` repo uses semantic versioning:

| Tag | Meaning |
|-----|---------|
| `v1.0.0` | Specific release |
| `v1` | Floating tag — latest stable in v1 series |
| `@v1` | What callers should pin to |

Use `@main` during initial testing, then switch to `@v1` after the first stable release.

To create a release:

```bash
cd devops-template
./scripts/shell/tag-release.sh v1.0.0
```
