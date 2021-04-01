# Tests Guidelines

This section describes how to run the test suite of the VAST Pipeline.

## General Tests

Test are found under the folder [tests](https://github.com/askap-vast/vast-pipeline/blob/master/vast_pipeline/tests/){:target="_blank"}. Have a look and feel free to include new tests.

Run the tests with the following:

To run all tests:

```bash
(pipeline_env)$ ./manage.py test
```

To run one test file or class, use:

```bash
(pipeline_env)$ ./manage.py test <path.to.test>
```

for example, to run the test class `CheckBasicRunConfigValidationTest` located in [`test_pipelineconfig.py`](https://github.com/askap-vast/vast-pipeline/blob/master/vast_pipeline/tests/test_pipelineconfig/test_pipelineconfig.py){:target="_blank"}, use:

```bash
(pipeline_env)$ ./manage.py test vast_pipeline.tests.test_pipelineconfig.test_pipelineconfig.CheckBasicRunConfigValidationTest
```

to run the tests located in [`test_webserver.py`](https://github.com/askap-vast/vast-pipeline/blob/master/vast_pipeline/tests/test_webserver.py){:target="_blank"}, use:

```bash
(pipeline_env)$ ./manage.py test vast_pipeline.tests.test_webserver
```

## Regression Tests

Regression tests located in [`test_regression`](https://github.com/askap-vast/vast-pipeline/blob/master/vast_pipeline/tests/test_regression/){:target="\_blank"} require the use of the _VAST\_2118-06A_ field test dataset which is not a part of the repository. This data is downloadable from [cloudstor](https://cloudstor.aarnet.edu.au/plus/s/xjh0aRr1EGY6Bt3){:target="_blank"}. You can use the script located in [tests/regression-data/](https://github.com/askap-vast/vast-pipeline/blob/master/vast_pipeline/tests/regression-data/){:target="_blank"}:

```bash
cd vast_pipeline/tests/regression-data/ && ./download.sh
```

to download the _VAST\_2118-06A_ field test dataset into the [`regression-data`](https://github.com/askap-vast/vast-pipeline/blob/master/vast_pipeline/tests/regression-data/){:target="_blank"} folder. Or manually by clicking the button below:

[Download data for test :material-cloud-download-outline:](https://cloudstor.aarnet.edu.au/plus/s/xjh0aRr1EGY6Bt3/download){: .md-button target="_blank"}

and place the _VAST\_2118-06A_ field test dataset into the [`regression-data`](https://github.com/askap-vast/vast-pipeline/blob/master/vast_pipeline/tests/regression-data/){:target="_blank"} folder. These regression tests are skipped if the dataset is not present.

All tests should be run before pushing to master. Running all the tests takes a few minutes, so it is not recommended to run them for every change.

If you have made a minor change and would like to only run unit tests, skipping regression tests, use:

```bash
(pipeline_env)$ ./manage.py test vast_pipeline.tests.test_pipeline
```

!!! note
    If changes are made to the default config keys, these changes need to be propagated to the test config files.
