# GitHub platform guidelines

This section explains how to interact with GitHub platform for opening Issues and Pull Requests, and some notes how to make a release of the pipeline if you are a mantainer of the code base.

## Issues Guidelines

* Please search for a similar issue before opening a new one by run a search on the [issue page](https://github.com/askap-vast/vast-pipeline/issues){:target="_blank"} with specific key-words.
* When opening a new issue, please specify the issue type (e.g. bug, feature, etc.) and provide a detailed description with use cases if applied.


## Pull Request Guideline

### Opening a PR

!!! tip "First consider . . ."

    1. search among the issues for similar problems/bugs/etc
    2. opening an issue before creating/issuing the PR.

    So we can separate problems from solutions.

Steps to issue a pull request:

1. Open an issue (e.g. `My issue blah`, GitHub will assign a id e.g. `#123`).
2. Branch off `master` by naming your branch `fix-#123-my-issue-blah` (keep it short please).
3. Do your changes.
4. Run test locally with `./manage.py test vast_pipeline` (see the [complete guide on the test](./tests.md) for more details).
5. Run the webserver and check the functionality.
6. Commit and issue the PR.
7. Assign the review to one or more reviewers if none are assigned by default.

!!! warning "Warning"

    PRs not branched off master will be __rejected__!.

### Pull Request Review Guidelines
The guidelines to dealing with reviews and conversations on GitHub are essentially:

* Be nice :smile: with the review and do not offend the author of the PR: __Nobody is a perfect developer or born so!__
* The reviewers will in general mark the conversation as "resolved" (e.g. he/she is satisfied with the answer from the PR author).
* The PR author will re-request the review by clicking on the :octicons-sync-16: on the top right corner and might ping the reviewer on a comment if necessary with `@github_name`.
* When the PR is approved by at least one reviewer you might want to merge it to master (you should have that privileges), unless you want to make sure that such PR is reviewed by another reviewer (e.g. you are doing big changes or important changes or you want to make sure that other person is aware/updated about the changes in that PR).

## Releasing Guidelines

In to order to make a release, please follow these steps (example: making the `0.1.0` release):

1. Make sure that every new feature and PR will be merged to master, before continuing with the releasing process.
2. Update the [`CHANGELOG.md`](https://github.com/askap-vast/vast-pipeline/blob/master/CHANGELOG.md){:target="_blank"} on `master` directly (only admin can and need to force-push the changes) with the list of changes. An example of format can be found [here](https://github.com/apache/incubator-superset/blob/master/CHANGELOG.md){:target="_blank"}.
3. Update the "announcement bar" in the documentation to refer to the new release. This can be found in `docs/custom_home/main.html` at line 37.
4. The `0.2.X` branch will be updated by merging `master` into `0.2.X`.
5. Branch off `0.2.X` and call it `0.2.1`, then change the `package.json` with the version of the release, commit and tag the commit. Push commit and tag to origin.
6. Make a release in GitHub using that tag.

__NOTE__: keep the version on `master` branch to something like 99.99.99dev and in `0.2.X` branch to something like 0.2.99dev. In the release branch, change only the version in [`package.json`](https://github.com/askap-vast/vast-pipeline/blob/master/package.json){:target="_blank"}.
