# Development Guidelines for Documentation

The pipeline documentation has been developed using the python package `mkdocs`and the [material theme](https://squidfunk.github.io/mkdocs-material/){:target="_blank"}. It is published as a static website using GitHub pages.

## Documentation development server

This section describes how to set up a development server to live reload your changes to the pipeline documentation.

The main code of the documentation is under the `docs` folder, with fews hacks: in order to keep the repository `README.md`, `CHANGELOG.md`, `LICENSE.txt` and `CODE_OF_CONDUCT.md` on the root path, relative soft links have been created under the docs folder:

```bash
architecture
changelog.md -> ../CHANGELOG.md
code_of_conduct.md -> ../CODE_OF_CONDUCT.md
developing
img
license.md -> ../LICENSE.txt
quickstart
README.md -> ../README.md
theme
usage
```

Start the development server:

```bash
(pipeline_env)$ mkdocs serve
```

And start to modify/add the documentation by changing the markdown files under the `docs` folder.

The structure of the site (see `nav` section) and the settings are in the `mkdocs.yml` in the root of the repository.

`mkdocs` and the material theme have a lot of customizations and plugins, so please refer to their documentation.

Python docstrings and source code can be rendered using the `mkdocstrings` plugin: for example rendering `models.py` functions docstrings can be done with:

```md
::: vast_pipeline.models
```

More details on how to display the source code and additional tweaks can be found in [mkdocstrings documentation](https://pawamoy.github.io/mkdocstrings/usage/){:target="_blank"}.

## Deployment to GitHub pages

Automatic deployment to GitHub pages is set up using GitHub actions and workflows. See source code under the `.github` folder.
