# GitHub platform guidelines

This section explains how to interact with GitHub platform for opening Issues and Pull Requests, and some notes how to make a release of the pipeline if you are a mantainer of the code base.

## Issues Guidelines

* Please search for a similar issue before opening a new one by run a search on the [issue page](https://github.com/askap-vast/vast-pipeline/issues) with specific key-words.
* When opening a new issue, please specify the issue type (e.g. bug, feature, etc.) and provide a detailed description with use cases if applied.


## Pull Request Guideline
First consider
>opening an issue before creating/issuing the PR.

So we can separe problems from solutions.

1. Open an issue (e.g. `My issue blah`, GitHub will assign a id e.g. `#123`).
2. Branch off `master` by naming your branch `fix-#123-my-issue-blah` (keep it short please).
3. Do your changes.
4. Run one or more pipeline run on full images to test functionality.
5. Run test locally with `./manage.py test vast_pipeline` (see the [complete guide on the test](tests) for more details).
6. Run the webserver and check the functionality.
7. Commit and issue the PR.

PRs not branched off master will be __rejected__!.

## Releasing Guidelines

In to order to make a release, please follow these steps (example: making the `0.1.0` release):

1. Make sure that every new feature and PR will be merged to master, before continuing with the releasing process.
2. Update the [`CHANGELOG.md`](https://github.com/askap-vast/vast-pipeline/blob/master/CHANGELOG.md) on `master` directly (only admin can and need to force-push the changes) with the list of changes. An example of format can be found [here](https://github.com/apache/incubator-superset/blob/master/CHANGELOG.md).
3. The `0.2.X` branch will be updated by merging `master` into `0.2.X`.
4. Branch off `0.2.X` and call it `0.2.1`, then change the `package.json` with the version of the release, commit and tag the commit. Push commit and tag to origin.
5. Make a release in GitHub using that tag.

__NOTE__: keep the version on `master` branch to something like 99.99.99dev and in `0.2.X` branch to something like 0.2.99dev. In the release branch, change only the version in [`package.json`](https://github.com/askap-vast/vast-pipeline/blob/master/package.json).
