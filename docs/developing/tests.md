# Tests Guidelines

Test are found under the folder [tests](https://github.com/askap-vast/vast-pipeline/blob/master/vast_pipeline/tests/). Have a look and feel free to include new tests.

Run the tests with the following:

To run all tests:
```bash
(pipeline_env)$ ./manage.py test
```

To run one test file or class, use:
```bash
(pipeline_env)$ ./manage.py test <path.to.test>
```
for example, to run the test class `CheckRunConfigValidationTest` located in [`test_runpipeline.py`](https://github.com/askap-vast/vast-pipeline/blob/master/vast_pipeline/tests/test_runpipeline.py), use:
```bash
(pipeline_env)$ ./manage.py test vast_pipeline.tests.test_runpipeline.CheckRunConfigValidationTest
```
to run the tests located in [`test_webserver.py`](https://github.com/askap-vast/vast-pipeline/blob/master/vast_pipeline/tests/test_webserver.py), use:
```bash
(pipeline_env)$ ./manage.py test vast_pipeline.tests.test_webserver
```

Regression tests located in [`test_regression.py`](https://github.com/askap-vast/vast-pipeline/blob/master/vast_pipeline/tests/test_regression.py) requires the use of the _VAST_2118-06A_ field test dataset which is not a part of the repository. This data is downloadable at https://cloudstor.aarnet.edu.au/plus/s/m2eRb27MIMNM7LM, use:
```bash
wget https://cloudstor.aarnet.edu.au/plus/s/m2eRb27MIMNM7LM/download
```
place the _VAST_2118-06A_ field test dataset in a folder named `regression-data` inside the [tests](https://github.com/askap-vast/vast-pipeline/blob/master/vast_pipeline/tests/) folder. These regression tests are skipped if the data folder containing the dataset is not present.

All tests should be run before pushing to master. Running all the tests takes a few minutes, so it is not recommended to run them for every change.
