# GitHub Platform Guidelines

This section explains how to interact with GitHub platform for opening issues, starting discussions, creating pull requests (PR), and some notes how to make a release of the pipeline if you are a maintainer of the code base.

The VAST team uses the "git flow" branching model which we briefly summarise here. More detail can be found [here](https://nvie.com/posts/a-successful-git-branching-model/).

There are two main branches, both with infinite lifetimes (they are never deleted):

- `master` for stable, production-ready code that has been released, and
- `dev` for the latest reviewed updates for the next release.

Other branches for bug fixes and new features are created as needed, branching off and merging back into `dev`. An exception to this is for critical patches for a released version called a "hotfix". These are branched off `master` and merged back into both `master` and `dev`.

Branches are also created for each new release candidate, which are branched off `dev` and merged into `master` and `dev` when completed. See the [Releases](#releases) section below for more information.

## Issues

An issue can be created by anyone with access to the repository. Users are encouraged to create issues for problems they encounter while using the pipeline or to request a new feature be added to the software. Issues are created by clicking the "New issue" button near the top-right of the [issues page](https://github.com/askap-vast/vast-pipeline/issues){:target="_blank"}.

When creating a new issue, please consider the following:

* Search for a similar issue before opening a new one by using the search box near the top of the issues page.
* When opening a new issue, please specify the issue type (e.g. bug, feature, etc.) and provide a detailed description with use cases when appropriate.

## Discussions

GitHub repositories also have a discussions page which serves as a collaborative forum to discuss ideas and ask questions. Users are encouraged to ask general questions, or start a conversation about potential new features to the software by creating a new discussion thread on the [discussions page](https://github.com/askap-vast/vast-pipeline/discussions){:target="_blank"}. Note that new software features may also be requested by creating an issue, but a discussion thread is more appropriate if the details of the new feature are still yet to be determined or require wider discussion – issues can be created from discussions once a consensus is reached.

## Pull Requests

Pull requests are created when a developer wishes to merge changes they have made in a branch into another branch. They enable others to review the changes and make comments. While issues typically describe in detail a specific problem or proposed feature, pull requests contain a detailed description and the required code changes for a solution to a problem or implementation of a new feature.

### Opening a PR

!!! tip "First consider ..."

    1. Search existing issues for similar problems or feature proposals.
    2. Opening an issue to describe the problem or feature before creating a PR. This will help separate problems from solutions.

Steps to issue a pull request:

1. Create a new issue on GitHub, giving it a succinct title and describe the problem. GitHub will assign an ID e.g. `#123`.
2. Create a new branch off the `dev` branch and name the branch based on the issue title, e.g. `fix-123-some-problem` (keep it short please).
3. Make your changes.
4. Run the test suite locally with `python manage.py test vast_pipeline`. See the [complete guide on the test](./tests.md) for more details.
5. Run the webserver and check the functionality. This is important as the test suite does not currently check the web UI.
6. Commit the changes to your branch, push it to GitHub, and open a PR for the branch.
7. Update the `CHANGELOG.md` file by adding the link to your PR and briefly describing the changes. An example of the change log format can be found [here](https://github.com/apache/incubator-superset/blob/dev/CHANGELOG.md){:target="_blank"}
8. Assign the review to one or more reviewers if none are assigned by default.

!!! warning "Warning"

    PRs not branched off dev will be __rejected__!.

### Reviewing a PR

The guidelines to dealing with reviews and conversations on GitHub are essentially:

* Be nice :smile: with the review and do not offend the author of the PR: __Nobody is a perfect developer or born so!__
* The reviewers will in general mark the conversation as "resolved" (e.g. he/she is satisfied with the answer from the PR author).
* The PR author will re-request the review by clicking on the :octicons-sync-16: on the top right corner and might ping the reviewer on a comment if necessary with `@github_name`.
* When the PR is approved by at least one reviewer you might want to merge it to dev (you should have that privileges), unless you want to make sure that such PR is reviewed by another reviewer (e.g. you are doing big changes or important changes or you want to make sure that other person is aware/updated about the changes in that PR).

## Releases

In to order to make a release, please follow these steps:

1. Make sure that all new feature and bug fix PRs that should be part of the new release have been merged to `dev`.
2. Checkout the `dev` branch and update it with `git pull`. Ensure that there are no uncommitted changes.
3. Create a new branch off `dev`, naming it `release-vX.Y.Z` where `X.Y.Z` is the new version. Typically, patch version increments for bug fixes, minor version increments for new features that do not break backward compatibility with previous versions (i.e. no database schema changes), and major version increments for large changes or for changes that would break backward compatibility.
4. Bump the version number of the Python package using Poetry, i.e. `poetry version X.Y.Z`. This will update the version number in `pyproject.toml`.
5. Update the version in `package.json` and `vast_pipeline/_version.py` to match the new version number.
6. Update the "announcement bar" in the documentation to refer to the new release. This can be found in `docs/theme/main.html` at line 37.
7. Update the [`CHANGELOG.md`](https://github.com/askap-vast/vast-pipeline/blob/master/CHANGELOG.md){:target="_blank"} by making a copy of the "Unreleased" heading at the top, and renaming the second one to the new version. After this there should be an "Unreleased" heading at the top, immediately followed by another heading with the new version number, which is followed by all the existing changes.
8. Commit all the changes made above to the new branch and push it to GitHub.
9. Open a PR to merge the new branch into `master`. Note that the default target branch is `dev` so you will need to change this to `master` when creating the PR.
10. Once the PR has been reviewed and approved, merge the branch into `master`. This can only be done by administrators of the repository.
11. Tag the merge commit on `master` with the version, i.e. `git tag vX.Y.Z`.

    !!! warning
        If you merged the release branch into `master` with the GitHub web UI, you will need to sync that merge to your local copy and checkout `master` before creating the tag. You cannot create tags with the GitHub web UI.

12. Push the tag to GitHub, i.e. `git push origin vX.Y.Z`.
13. Merge the release branch into `dev`, resolving any conflicts.
14. Append "dev" to the version numbers in `pyproject.toml`, `package.json` and `vast_pipeline/_version.py` and commit the change to `dev`.  This can either be done as a new commit, or while resolving merge conflicts in the previous step, if appropriate.
