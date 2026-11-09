# Prints the maker-portal steps for the sample solution used to prove this pipeline.
# After the canvas app is inside the solution in L48 DEV, run Export-Solution.ps1.

[CmdletBinding()]
param(
    [string] $EnvironmentUrl = ""
)

$ErrorActionPreference = "Stop"
$SolutionName = "SamplePipelineApp"
$PublisherName = "L48"
$PublisherPrefix = "l48"
$DisplayName = "Sample Pipeline App"

Write-Host "Sample solution: $SolutionName"
Write-Host ""
Write-Host "1. Install Power Platform CLI if pac is not on PATH:"
Write-Host "   dotnet tool install --global Microsoft.PowerApps.CLI.Tool"
Write-Host ""
Write-Host "2. In L48 DEV, open Solutions in the maker portal:"
Write-Host "   https://make.powerapps.com/"
if (-not [string]::IsNullOrWhiteSpace($EnvironmentUrl)) {
    Write-Host "   Environment URL: $($EnvironmentUrl.Trim().TrimEnd('/'))"
}
Write-Host ""
Write-Host "3. Create a publisher once for this pipeline, then reuse it for every app:"
Write-Host "   Display name: $PublisherName"
Write-Host "   Name: $PublisherPrefix"
Write-Host "   Prefix: $PublisherPrefix"
Write-Host "   Choice value prefix: 10000"
Write-Host ""
Write-Host "4. Create the solution:"
Write-Host "   Display name: $DisplayName"
Write-Host "   Name: $SolutionName"
Write-Host "   Publisher: $PublisherName"
Write-Host "   Version: 1.0.0.0"
Write-Host ""
Write-Host "5. Inside that solution, create the components you want the pipeline to carry:"
Write-Host "   - Canvas app: New > App > Canvas app. Add a label that says Pipeline sample. Save and publish."
Write-Host "   - Cloud flow: New > Automation > Cloud flow > Instant. One Compose action is enough. Save."
Write-Host "   - Table: New > Table. Name it Pipeline Sample. One text column is enough. Save."
Write-Host ""
Write-Host "6. Confirm all three components are listed on the solution, not only in the environment."
Write-Host ""
Write-Host "7. Export that unmanaged solution into this repo. Replace the URL with L48 DEV:"
Write-Host "   .\scripts\Export-Solution.ps1 -SolutionName $SolutionName -EnvironmentUrl https://<l48-dev>.crm.dynamics.com -DisplayName '$DisplayName' -BranchName feature/$SolutionName/initial"
Write-Host ""
Write-Host "8. Open a pull request from that feature branch into main."
Write-Host "   The PR runs quality validation and solution checker."
Write-Host "   Merge to main packs one managed zip, deploys it to TEST, then waits."
Write-Host "   A reviewer approves the prod deployment. PROD imports that same zip."
Write-Host "   The pipeline then creates tag release/$SolutionName/<version>."

if (Get-Command pac -ErrorAction SilentlyContinue) {
    Write-Host ""
    Write-Host "pac is already on PATH."
}
else {
    Write-Host ""
    Write-Host "pac is not installed yet. Install the .NET SDK, then the CLI command above."
}
