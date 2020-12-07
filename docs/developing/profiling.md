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
