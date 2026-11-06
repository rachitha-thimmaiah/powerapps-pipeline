# Solutions

Each application has one folder, named with its Dataverse solution unique name:

```text
solutions/SamplePipelineApp/
solutions/ClaimsReview/
solutions/SiteInspection/
```

A feature branch should carry one solution: `feature/<SolutionUniqueName>/<change>`.

The pipeline builds only the folders a commit changes. Fifty applications can share this repository and still promote independently.
