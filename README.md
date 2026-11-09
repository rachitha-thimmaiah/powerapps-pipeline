# Power Apps promotion pipeline

This repository promotes Power Apps solutions from L48 DEV to TEST and then PROD. One managed zip is packed on `main`. TEST and PROD both import that zip. PROD starts only after a reviewer uses the deployment approval button, and a release tag is created after PROD succeeds.

Each application is one solution folder and can use its own feature branch. A commit that changes one folder does not rebuild the other applications.

```text
Developer in L48 DEV
  canvas app, flow, Dataverse schema
        |
        v
scripts/Export-Solution.ps1
  unmanaged export, unpack as Both, commit feature/<Solution>/<change>
        |
        v
Pull request
  .github/workflows/pr-validate.yml
  quality validation of the unpacked files
        |
        v
Merge to main
        |
        v
Build and promote
  pack managed zip once
  upload artifact managed-<Solution>
        |
        v
Deploy TEST
  solution checker, then import that zip, publish, smoke test
        |
        v
Review deployments  ->  Approve prod
        |
        v
Deploy PROD
  import the same zip, no second pack
        |
        v
Tag release/<Solution>/<version>
```

## Workflows

| Workflow | When it runs | What it does |
| --- | --- | --- |
| [PR validation](.github/workflows/pr-validate.yml) | Every pull request to `main` | Checks the unpacked solution files |
| [Build and promote](.github/workflows/release.yml) | Push to `main` that changes a solution, or a manual rebuild | Packs, runs solution checker, deploys TEST, waits, deploys PROD, tags |
| [Redeploy managed artifact](.github/workflows/redeploy-artifact.yml) | Manual | Imports an existing artifact again, without packing |

## Add an application

1. In L48 DEV, create a solution with the shared publisher prefix.
2. Make the canvas, flow, and schema changes inside that solution.
3. Export it:

```powershell
.\scripts\Export-Solution.ps1 `
  -SolutionName ClaimsReview `
  -EnvironmentUrl https://<l48-dev>.crm.dynamics.com `
  -DisplayName "Claims Review" `
  -BranchName feature/ClaimsReview/initial
```

4. Open a pull request. After it merges, approve the prod deployment in the Actions run.

`catalog/solutions.json` is the list of applications. `enabled: false` keeps the sample placeholder out of the pipeline until it has been exported.

## Setup

The pipeline does not run until the repository is on GitHub and Entra trusts it.

1. [Create one app registration, two federated credentials, the application users, and the GitHub environments](docs/entra-federated-credentials.md).
2. [Create `SamplePipelineApp` in L48 DEV and export it](docs/sample-solution.md).
3. Require the `PR validation` status check on `main`.
4. Add release managers as required reviewers on the GitHub environment named `prod`.

GitHub environment names are part of the federated credential subject. Use `test` and `prod`.

## Authentication

One app registration is used. Its federated credentials trust only `repo:<org>/<repo>:environment:test` and `repo:<org>/<repo>:environment:prod`. Pull requests do not receive a token. Solution checker runs in the TEST job, before import, with that same app. Client secrets are not used.

Repository variables are `PP_TENANT_ID`, `PP_APP_ID`, and `PP_CHECKER_GEO`. The TEST and PROD URLs are environment variables named `PP_ENVIRONMENT_URL` on those GitHub environments.
