import logging
import math
import os

from glob import glob
from tqdm import tqdm
import dask.dataframe as dd
from django.db import connection
from django.db import transaction
from vast_pipeline.utils.utils import StopWatch

logger = logging.getLogger(__name__)

def _run_raw_sql(command, cursor, debug=False, log=True, dry_run=False):
    if log:
        if debug:
            logger.debug("Running %s", command)
        else:
            logger.info("Running %s", command)
    if not dry_run:
        cursor.execute(command)
    
    return

def delete_pipeline_run_raw_sql(p_run, source_batch_size=10000, delete_images=False):
    p_run_id = p_run.pk

    with transaction.atomic():
        with connection.cursor() as cursor:
            #####
            #
            # Step 1: handle sources
            #
            #####
            timer = StopWatch()
            clear_run_sources(p_run_id, batch_size=source_batch_size, timer=timer)
            
            #####
            #
            # Step 2: Handle images
            #
            #####

            # Fetch image IDs associated with the pipeline run
            timer.reset()
            sql_cmd = f"SELECT image_id FROM vast_pipeline_image_run WHERE run_id = {p_run_id};"
            _run_raw_sql(sql_cmd, cursor)
            image_ids = cursor.fetchall()
            n_image_ids = len(image_ids)
            image_id_str = ','.join(str(image_id[0]) for image_id in image_ids)
            logger.debug(f"images associated with run: {image_id_str}")
            
            if n_image_ids > 0:
                # Only delete the actual images if selected, but only delete if they're not linked to other runs
                if delete_images:
                    # Get the images that are uniquely associated with the pipeline run
                    sql_cmd = f"SELECT image_id FROM vast_pipeline_image_run GROUP BY image_id HAVING COUNT(*) = 1 AND MAX(run_id) = {p_run_id};"
                    _run_raw_sql(sql_cmd, cursor)
                    unique_image_ids = cursor.fetchall()
                    unique_image_id_str = ','.join(str(image_id[0]) for image_id in unique_image_ids)
                    logger.debug(f"Iterating over image_ids unique to run: {unique_image_id_str}")

                    # ...and delete the measurements associated with them
                    for image_id_tuple in unique_image_ids:
                        image_id = image_id_tuple[0]
                        try:
                            sql_cmd = (
                                f"DELETE FROM vast_pipeline_association "
                                f"WHERE meas_id IN (SELECT id FROM vast_pipeline_measurement WHERE image_id = {image_id});"
                            )
                            _run_raw_sql(sql_cmd, cursor)

                            sql_cmd = f"DELETE FROM vast_pipeline_measurement WHERE image_id = {image_id};"
                            _run_raw_sql(sql_cmd, cursor)
                        except Exception as e:
                            logger.error("Failed to delete measurements for %s: %s", e, image_id)
                            raise

                # Delete link between run and images for all images
                sql_cmd = f"DELETE FROM vast_pipeline_image_run WHERE run_id = {p_run_id} AND image_id IN ({image_id_str});"
                _run_raw_sql(sql_cmd, cursor)

                # Delete images that are uniquely associated with the run
                if delete_images:
                    if len(unique_image_ids) > 0:
                        try:
                            sql_cmd = f"DELETE FROM vast_pipeline_image WHERE id IN ({unique_image_id_str});"
                            _run_raw_sql(sql_cmd, cursor)
                        except Exception as e:
                            logger.error("Failed to delete image for %s: %s", unique_image_id_str, e)
                            raise

                
                t = timer.reset()
                logger.info("Time to iterate over %d image ids: %f seconds", n_image_ids, t)
            else:
                logger.info("No images to delete...")

                    
            #####
            #
            # Step 3: Handle skyregions
            #
            #####

            # Fetch skyregion IDs associated with the pipeline run
            sql_cmd = f"SELECT skyregion_id FROM vast_pipeline_skyregion_run WHERE run_id = {p_run_id};"
            _run_raw_sql(sql_cmd, cursor, debug=True)
            sky_ids = cursor.fetchall()
            
            # Delete all rows from vast_pipeline_skyregion_run for the run:
            sql_cmd = f"DELETE FROM vast_pipeline_skyregion_run WHERE run_id = {p_run_id};"
            _run_raw_sql(sql_cmd, cursor)
            
            for sky_id_tuple in sky_ids:
                sky_id = sky_id_tuple[0]
                sql_cmd = f"SELECT COUNT(*) FROM vast_pipeline_image WHERE skyreg_id = {sky_id};"
                _run_raw_sql(sql_cmd, cursor)
                
                image_count = cursor.fetchone()[0]
                # Delete skyregions that no longer have an image associated with them
                if image_count > 0:
                    logger.debug("Not deleting skyregion_id %s; %d image(s) still reference it.", sky_id, image_count)
                    continue
                else:
                    sql_cmd = f"DELETE FROM vast_pipeline_skyregion WHERE id = {sky_id};"
                    _run_raw_sql(sql_cmd, cursor)

            #####
            #
            # Step 4: Final cleanup steps
            #
            #####

            # Delete comments
            sql_cmd = f"DELETE FROM vast_pipeline_comment WHERE object_id = {p_run_id};"
            _run_raw_sql(sql_cmd, cursor)

            # Finally delete the pipeline run
            sql_cmd = f"DELETE FROM vast_pipeline_run WHERE id = {p_run_id};"
            _run_raw_sql(sql_cmd, cursor)

def clear_run_sources(p_run_id, batch_size=10_000, timer=None):
    """
    Clear the existing sources associated with a run
    
    Args:
        run: the pipeline run to clear
    """

    if timer is None:
        timer = StopWatch()

    with connection.cursor() as cursor:
        sql_cmd = f"SELECT id FROM vast_pipeline_source WHERE run_id = {p_run_id};"
        _run_raw_sql(sql_cmd, cursor)
        source_ids = cursor.fetchall()

        # Iterate over each source ID and delete related information
        n_source_ids = len(source_ids)
        logger.info("Iterating over %d sources to delete tags and relations", n_source_ids)
        n_batches = round(n_source_ids/batch_size)
        logger.info("Using %d batches of %d sources", n_batches, batch_size)

        batch_starts = list(range(0, len(source_ids), batch_size))
        timer.reset()
        for batch_start in tqdm(batch_starts):
            batch = source_ids[batch_start:batch_start+batch_size]
            batch_str = ','.join(str(source_id[0]) for source_id in batch)

            # Delete entries from vast_pipeline_sourcefav for each source_id
            sql_cmd = f"DELETE FROM vast_pipeline_sourcefav WHERE source_id IN ({batch_str});"
            _run_raw_sql(sql_cmd, cursor, log=False)

            # Find source tags related to the source and delete them
            sql_cmd = f"SELECT tagulous_source_tags_id FROM vast_pipeline_source_tags WHERE source_id IN ({batch_str});"
            _run_raw_sql(sql_cmd, cursor, log=False)
            tag_ids = cursor.fetchall()
            if tag_ids:
                tag_ids_str = ','.join(str(t[0]) for t in tag_ids)
                sql_cmd = f"DELETE FROM vast_pipeline_tagulous_source_tags WHERE id IN ({tag_ids_str});"
                _run_raw_sql(sql_cmd, cursor, log=False)

            # Delete from vast_pipeline_source_tags for the source_id
            sql_cmd = f"DELETE FROM vast_pipeline_source_tags WHERE source_id IN ({batch_str});"
            _run_raw_sql(sql_cmd, cursor, log=False)

            # Delete from related source
            sql_cmd = f"DELETE FROM vast_pipeline_relatedsource WHERE from_source_id IN ({batch_str});"
            _run_raw_sql(sql_cmd, cursor, log=False)
            sql_cmd = f"DELETE FROM vast_pipeline_relatedsource WHERE to_source_id IN ({batch_str});"
            _run_raw_sql(sql_cmd, cursor, log=False)

            # Delete from association
            sql_cmd = f"DELETE FROM vast_pipeline_association WHERE source_id IN ({batch_str});"
            _run_raw_sql(sql_cmd, cursor, log=False)

        t = timer.reset()
        logger.info("Time to iterate over %d source ids: %.2f seconds", n_source_ids, t)

        # Delete source
        sql_cmd = f"DELETE FROM vast_pipeline_source WHERE run_id = {p_run_id};"
        _run_raw_sql(sql_cmd, cursor)
        
        t = timer.reset()
        logger.info("Time to delete source objects: %.2f seconds", t)

def remove_forced_meas(run_path: str, batch_size: int = 10000) -> None:
    """
    Remove forced measurements from the database if forced parquet files
    are found.

    Args:
        run_path:
            The run path of the pipeline run.
        batch_size:
            Number of forced measurements to delete per iteration.

    Returns:
        None
    """
    path_glob = glob(os.path.join(run_path, "forced_measurements_*.parquet"))

    # Collect all forced measurement IDs from every parquet file simultaneously
    if not path_glob:
        logger.info("No forced measurement parquet files found in %s", run_path)
        return
    all_ids = dd.read_parquet(path_glob, columns=["id"])["id"].compute().tolist()

    if not all_ids:
        logger.info("No forced measurements found in parquet files in %s", run_path)
        return

    n_ids = len(all_ids)
    n_batches = math.ceil(n_ids / batch_size)
    logger.info(
        "Deleting %d forced measurements in %d batches of %d",
        n_ids, n_batches, batch_size,
    )

    timer = StopWatch()
    total_deleted = 0
    batch_starts = list(range(0, n_ids, batch_size))
    with connection.cursor() as cursor:
        for i in tqdm(batch_starts):
            batch = all_ids[i : i + batch_size]
            id_str = ",".join(f"'{mid}'" for mid in batch)

            # Remove associations first (FK constraint)
            cursor.execute(
                f"DELETE FROM vast_pipeline_association WHERE meas_id IN ({id_str});"
            )

            # Delete the measurements themselves
            cursor.execute(
                f"DELETE FROM vast_pipeline_measurement WHERE id IN ({id_str});"
            )
            total_deleted += cursor.rowcount

    t = timer.reset()
    logger.info(
        "Deleted %d forced measurements in %.2f seconds", total_deleted, t
    )
