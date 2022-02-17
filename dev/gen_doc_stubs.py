#!/usr/bin/env python

from pathlib import Path
import mkdocs_gen_files


# only allow certain directory trees from vast_pipeline.
exclude_dirs = ['migrations', 'tests']

# Problem files because of Django and mkdocs
# See https://github.com/mkdocstrings/mkdocstrings/issues/141
# __init__ is there just to avoid building these.
# TODO: Fix Django pages for mkdocs.
problem_files = ['serializers.py', 'views.py', '__init__.py', '_version.py']

for path in Path("vast_pipeline").glob("**/*.py"):

    if len(path.parts) > 2 and path.parts[1] in exclude_dirs:
        continue

    if path.name in problem_files:
        continue

    doc_path = Path(
        "reference", path.relative_to("vast_pipeline")
    ).with_suffix(".md")

    with mkdocs_gen_files.open(doc_path, "w") as f:
        ident = ".".join(path.relative_to(".").with_suffix("").parts)
        print("::: " + ident, file=f)

    mkdocs_gen_files.set_edit_path(doc_path, Path("..", path))
