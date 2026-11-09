# Create the sample solution and run it through the pipeline

The sample proves the path from L48 DEV to a PROD tag. The repository does not contain a fake `Solution.xml`. Pack and import need a real unpack from Dataverse.

The sample solution unique name is `SamplePipelineApp`. Its catalog entry stays disabled until the export script writes the unpacked source.

## Install the CLI

Install the [.NET SDK](https://dotnet.microsoft.com/download), then:

```powershell
dotnet tool install --global Microsoft.PowerApps.CLI.Tool
pac help
```

Close and reopen the terminal if `pac` is not recognized. The tool directory is `%USERPROFILE%\.dotnet\tools`.

## Build the sample in L48 DEV

Run:

```powershell
.\scripts\New-SampleSolution.ps1 -EnvironmentUrl https://<l48-dev>.crm.dynamics.com
```

That script prints the maker-portal values. Create them in L48 DEV:

1. Open <https://make.powerapps.com/> and switch to L48 DEV.
2. Create a publisher named `L48` with prefix `l48`. Reuse this publisher for the other applications. Do not change the prefix later.
3. Create a solution:
   - Display name: `Sample Pipeline App`
   - Name: `SamplePipelineApp`
   - Publisher: `L48`
   - Version: `1.0.0.0`
4. Inside the solution, add one of each:
   - Canvas app with a label that says `Pipeline sample`. Save and publish the app.
   - Instant cloud flow with a single Compose action.
   - Dataverse table named `Pipeline Sample` with one text column.
5. Stay inside the solution and confirm the app, flow, and table are solution components.

For the next fifty applications, repeat this with a new solution name and the same publisher. Each solution gets its own folder and its own feature branch.

## Export into git

Sign-in uses your user account, not the pipeline app registration.

```powershell
.\scripts\Export-Solution.ps1 `
  -SolutionName SamplePipelineApp `
  -EnvironmentUrl https://<l48-dev>.crm.dynamics.com `
  -DisplayName "Sample Pipeline App" `
  -BranchName feature/SamplePipelineApp/initial
```

The script:

1. Authenticates to L48 DEV in the browser.
2. Exports the unmanaged solution.
3. Unpacks it with package type `Both`, which is what lets the pipeline pack a managed zip later.
4. Enables `SamplePipelineApp` in `catalog/solutions.json`.
5. Runs the same quality checks the pull request runs.

Commit `solutions/SamplePipelineApp` and `catalog/solutions.json`. Do not commit `out/`.

Open a pull request into `main`. The branch name for later changes is `feature/SamplePipelineApp/<change>`.

## What the pull request runs

The **PR validation** workflow selects every solution folder the pull request changes.

- Quality validation checks the unique name, the four-part version, an unmanaged manifest, the publisher prefix, and that no secret or zip was committed.
- Solution checker does not run on the pull request. With one app registration, a pull-request credential could also reach PROD. The checker runs in the TEST job after merge and before import.

Set branch protection on `main` to require a pull request and the status check named `PR validation`.

## What happens after merge

**Build and promote** runs on `main`:

1. Packs `SamplePipelineApp_managed.zip` once and uploads artifact `managed-SamplePipelineApp`.
2. Runs solution checker against TEST, then imports that zip, publishes customizations, activates flows, and checks that TEST shows the same version.
3. Waits on the `prod` environment.
4. After **Review deployments** → **Approve**, imports that same zip into PROD. There is no second pack.
5. Creates the annotated tag `release/SamplePipelineApp/1.0.0.0`.

The version in the tag comes from `Other/Solution.xml`. The next change must use a higher version, such as `1.0.0.1`, or the managed upgrade is rejected.

## Connection references

If the flow has a connection, generate settings from the unpacked folder and fill the TEST and PROD connection IDs:

```powershell
pac solution create-settings `
  --solution-folder .\solutions\SamplePipelineApp `
  --settings-file .\config\SamplePipelineApp\test.settings.json
```

Copy that file to `config/SamplePipelineApp/prod.settings.json` and replace the connection IDs and environment-variable values with the downstream ones. An example shape is in [examples/deployment-settings.json](examples/deployment-settings.json). Do not put client secrets in these files. Secret environment-variable values are entered in the target environment, not in git.

The import uses `test.settings.json` for TEST and `prod.settings.json` for PROD when those files exist.

## Run the same zip again

PROD approval already imports the artifact from the build. To import that zip again without packing:

1. Open the successful **Build and promote** run and copy the run ID from the URL.
2. Run **Redeploy managed artifact**.
3. Solution name: `SamplePipelineApp`.
4. Source run ID: the run you copied.
5. Target: `test` or `prod`.

Choosing `prod` waits for the same approval button. The workflow downloads `managed-SamplePipelineApp` from that run and imports it.

## Version already in TEST

Before exporting a change, set a higher solution version in the maker portal, or set it on the solution in L48 DEV and export again. Dataverse will not upgrade a managed solution to the same or a lower version.
