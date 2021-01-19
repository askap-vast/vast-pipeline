# Benchmarks

## Initial Profiling
These profiling tests were run with the pipeline codebase correspondent to commit [373c2ce](https://github.com/askap-vast/vast-pipeline/tree/373c2ceea0c6bf6b8f0bee2ec3f8d592f1d83373) (some commits after the first release).

Running on 12GB of data with 464MB peak memory usage takes 4 mins:
_performance:_ ~80% `final_operations`, ~10% `get_src_skyregion_merged_df`. `final_operations` calls other functions, out of these the largest is 50% in `make_upload_sources` which spends about 20% of time on `utils` `<method 'execute' of 'psycopg2.extensions.cursor' objects>`. The `get_src_skyregion_merged_df` time sink is in `threading` 15% of time is on `wait` (`final_operations` spends some time on `threading` as well, hence 15% > 10%).
_memory:_ 40% `pyarrow` `parquet` `write_table`, rest is mostly fragmented, some more `pyarrow` and some `pandas`

Running on 3MB of data with peak memory usage 176MB, takes 1.5s:
_performance:_ ~30% goes to pipeline (about 9% of this is `pickle`), ~11% goes to `read`, rest goes to django I think
_memory:_ 30% memory is spent on `django`, 20% is spent on `astropy/coordinates/matrix_utilities`, 10% on importing other modules, rest is fragmented quite small

Note that I didn't include the generation of the `images/*/measurements.parquet` or other files in these profiles.

## Database Update Operations
Delete (`Model.objects.all().delete()`) and reupload (`bulk_upload`) (in seconds)

| :material-arrow-down:columns\rows:material-arrow-right:  | 10^3^       | 10^4^       | 10^5^     |
| ------------- |-------------| ------------|-----------|
| 4             | 0.15        | 1.24        | 12.95     |
| 8             | 0.26        | 1.64        | 19.11     |
| 12            | 0.31        | 2.18        | 21.49     |

Per cell, 10^3^ rows is slower than 10^4^ and 10^5^ rows, possibly due to overhead. Best to avoid uploading 10^3^ rows each bulk_create call.

Django `bulk_update`

| :material-arrow-down:columns\rows:material-arrow-right:  | 10^3^       | 10^4^       |  10^5^    |
| ------------- |-------------| ------------|-----------|
| 4             | 3.39        | na          | na        |
| 8             | 4.38        | na          | na        |
| 12            | 5.50        | na          | na        |

I don't think there's any point testing 10^4^ or 10^5^ rows, it's obviously the worst performing function, and I've already had to force quit the terminal twice because keyboard interrupt didn't work.

SQL join as (`SQL_update` in `vast_pipeline.pipeline.loading`)

| :material-arrow-down:columns\rows:material-arrow-right:  | 10^3^       | 10^4^       |  10^5^    |
| ------------- |-------------| ------------|-----------|
| 4             | 0.016       | 0.11        | 3.08      |
| 8             | 0.019       | 0.32        | 4.31      |
| 12            | 0.027       | 0.38        | 5.39      |

10^5^ is slower per cell than 10^4^ and 10^3^, not sure why. Recommend updating 10^4^ rows each time.

This timing info does vary a bit on randomness. Sometimes the SQL join as takes as long as 1 second to complete 10^3^ rows, I'm not sure what's causing this.
