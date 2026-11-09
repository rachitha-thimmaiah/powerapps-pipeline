# One Entra app registration and federated credentials

GitHub Actions authenticates to Dataverse with OpenID Connect. The workflow asks GitHub for a short-lived token, and Entra accepts that token because a federated credential matches the token subject. No client secret is stored in GitHub.

One app registration is enough. Add two federated credentials to it, one for the GitHub `test` environment and one for `prod`. Do not add a pull-request credential and do not add a branch credential.

A pull-request credential on this same app would be unsafe. The app is an application user in TEST and PROD, and an Entra token is not limited to one Dataverse environment. Anyone who can push a branch could change the pull-request workflow and call PROD. GitHub only mints the token when a job is allowed to use the `test` or `prod` environment, and those environments are limited to `main`. The prod job also waits for a reviewer.

Leave the repository OIDC subject claim on its default. Do not switch it to the `repository, workflow` template. The subjects below depend on the GitHub environment name.

Replace `ORG/REPO` with the GitHub organization and repository, for example `rachitha-thimmaiah/powerapps-pipeline`.

## 1. Create the app registration

1. Open [Microsoft Entra admin center](https://entra.microsoft.com) → **Identity** → **Applications** → **App registrations** → **New registration**.
2. Name: `github-powerapps-alm`.
3. Supported account types: **Accounts in this organizational directory only**.
4. Leave the redirect URI empty. Register.
5. Copy **Application (client) ID** and **Directory (tenant) ID**.
6. **API permissions** → **Add a permission** → **APIs my organization uses** → search **Dataverse** (it may still be labeled Dynamics CRM) → **Delegated** → **user_impersonation** → **Add permission**.
7. Grant admin consent if your tenant requires it. This permission does not replace the application users created later.

Do not create a client secret.

## 2. Add the two federated credentials

Open **Certificates & secrets** → **Federated credentials** → **Add credential**. If the GitHub scenario is not listed, choose **Other** and enter:

- Issuer: `https://token.actions.githubusercontent.com`
- Audience: `api://AzureADTokenExchange`

### TEST

- Scenario: **GitHub Actions deploying Azure resources**
- Organization and repository: this repository
- Entity type: **Environment**
- GitHub environment name: `test`
- Name: `github-environment-test`
- Subject:

```text
repo:ORG/REPO:environment:test
```

### PROD

Add a second credential on the same app.

- Entity type: **Environment**
- GitHub environment name: `prod`
- Name: `github-environment-production`
- Subject:

```text
repo:ORG/REPO:environment:prod
```

The GitHub environment name and the subject must match. This repository uses the immutable subject, so the stored value includes the owner and repository IDs and ends in `:environment:prod`.

## 3. Application users in Power Platform

The app registration is not a Dataverse user until you add it in each environment that the pipeline imports into. Developers keep exporting from L48 DEV with their own accounts, so this app does not need access to DEV.

1. Open [Power Platform admin center](https://admin.powerplatform.microsoft.com).
2. Select the environment → **Settings** → **Users + permissions** → **Application users** → **New app user**.
3. **Add an app**, search `github-powerapps-alm`, and choose the root business unit.
4. Assign **System Administrator** and create the user.

Add that same app to both environments:

| Environment | App registration | Security role |
| --- | --- | --- |
| TEST | `github-powerapps-alm` | System Administrator |
| PROD | `github-powerapps-alm` | System Administrator |

System Administrator is the deploy role because solution import, publish, flow activation, and security-role updates fail under a narrower role.

If the app does not appear in **Add an app**, wait a few minutes after creating the registration and confirm you are in the same tenant.

Copy each environment URL from the environment details page. It looks like `https://contoso-test.crm.dynamics.com`. Do not include a trailing slash.

The Power Platform display name can be anything. The pipeline selects the Dataverse environment by this URL, not by the name shown in the maker portal.

## 4. GitHub variables and environments

In the repository, open **Settings** → **Secrets and variables** → **Actions** → **Variables**. Add repository variables:

| Variable | Value |
| --- | --- |
| `PP_TENANT_ID` | Directory (tenant) ID |
| `PP_APP_ID` | Application (client) ID of `github-powerapps-alm` |
| `PP_CHECKER_GEO` | `UnitedStates`, or the geo where the checker service runs |

Do not create a client secret. Do not put the TEST or PROD URLs in repository variables.

Create two GitHub environments under **Settings** → **Environments**.

### Environment `test`

- Environment variable `PP_ENVIRONMENT_URL` = TEST Dataverse URL
- Deployment branches: **Selected branches** → `main`

### Environment `prod`

- Environment variable `PP_ENVIRONMENT_URL` = PROD Dataverse URL
- Deployment branches: **Selected branches** → `main`
- **Required reviewers**: the release managers

The required reviewer is the play button. After solution checker and the TEST import succeed, the PROD job stays on **Waiting**. The reviewer opens the workflow run, selects **Review deployments**, and approves `prod`. That approval imports the same managed zip. It does not pack the solution again.

Also set **Settings** → **Actions** → **General** → **Workflow permissions** to **Read and write permissions**. The tag job needs that permission to push `release/<SolutionUniqueName>/<version>`.

## 5. Confirm the trust

- The TEST job **Verify TEST federated identity** returns a user id, then solution checker runs, and only then does the import start.
- PROD uses the same application ID and the PROD URL, and only after the approval button.

If sign-in fails with a subject or issuer error, compare the federated credential subject with the job:

- TEST: `repo:ORG/REPO:environment:test`
- PROD: `repo:ORG/REPO:environment:prod`

If sign-in succeeds and the import says the user is not authorized, the application user or its security role is missing in that environment.
