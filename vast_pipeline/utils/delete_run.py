import logging

from django.db import connection
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

def delete_pipeline_run_raw_sql(p_run, source_batch_size=1000, delete_images=True):
    p_run_id = p_run.pk

    with connection.cursor() as cursor:
        # Disable triggers
        #sql_cmd = "ALTER TABLE vast_pipeline_source DISABLE TRIGGER ALL;"
        #_run_raw_sql(sql_cmd, cursor)
        
        # Fetch source IDs associated with the pipeline run
        sql_cmd = f"SELECT id FROM vast_pipeline_source WHERE run_id = {p_run_id};"
        _run_raw_sql(sql_cmd, cursor)
        source_ids = cursor.fetchall()

        # Iterate over each source ID and delete related information
        n_source_ids = len(source_ids)
        logger.info("Iterating over %d sources to delete tags and relations", n_source_ids)
        n_batches = round(n_source_ids/source_batch_size)
        logger.info("Using %d batches of %d sources", n_batches, source_batch_size)
        
        timer = StopWatch()
        batch_starts = list(range(0, len(source_ids), BATCH_SIZE))
        for batch_start in tqdm(batch_starts):
            batch = source_ids[batch_start:batch_start+BATCH_SIZE]
            batch_str = ','.join(str(source_id[0]) for source_id in batch)

            # Delete entries from vast_pipeline_sourcefav for each source_id
            sql_cmd = f"DELETE FROM vast_pipeline_sourcefav WHERE source_id IN {batch_str};"
            _run_raw_sql(sql_cmd, cursor, log=False)

            # Find source tags related to the source and delete them
            sql_cmd = f"SELECT tagulous_source_tags_id FROM vast_pipeline_source_tags WHERE source_id IN {batch_str};"
            _run_raw_sql(sql_cmd, cursor, log=False)
            tag_ids = cursor.fetchall()
            if tag_ids:
                tag_ids_str = ','.join(str(t[0]) for t in tag_ids)
                sql_cmd = f"DELETE FROM vast_pipeline_tagulous_source_tags WHERE id IN ({tag_ids_str});"
                _run_raw_sql(sql_cmd, cursor, log=False)

            # Delete from vast_pipeline_source_tags for the source_id
            sql_cmd = f"DELETE FROM vast_pipeline_source_tags WHERE source_id IN {batch_str};"
            _run_raw_sql(sql_cmd, cursor, log=False)

            # Delete from related source
            sql_cmd = f"DELETE FROM vast_pipeline_relatedsource WHERE from_source_id IN {batch_str};"
            _run_raw_sql(sql_cmd, cursor, log=False)
            sql_cmd = f"DELETE FROM vast_pipeline_relatedsource WHERE to_source_id IN {batch_str};"
            _run_raw_sql(sql_cmd, cursor, log=False)

            sql_cmd = f"DELETE FROM vast_pipeline_association WHERE source_id IN {batch_str};"
            _run_raw_sql(sql_cmd, cursor, log=False)

        t = timer.reset()
        logger.info("Time to iterate over %d source ids: %.2f seconds", n_source_ids, t)

        # Delete source
        sql_cmd = f"DELETE FROM vast_pipeline_source WHERE run_id = {p_run_id};"
        _run_raw_sql(sql_cmd, cursor)
        
        t = timer.reset()
        logger.info("Time to delete source objects: %.2f seconds", t)
        
        # Enable triggers
        #sql_cmd = "ALTER TABLE vast_pipeline_source ENABLE TRIGGER ALL;"
        #_run_raw_sql(sql_cmd, cursor)

        # Delete comments
        sql_cmd = f"DELETE FROM vast_pipeline_comment WHERE object_id = {p_run_id};"
        _run_raw_sql(sql_cmd, cursor)

        # Fetch image IDs associated with the pipeline run
        sql_cmd = f"SELECT image_id FROM vast_pipeline_image_run WHERE run_id = {p_run_id};"
        _run_raw_sql(sql_cmd, cursor)
        image_ids = cursor.fetchall()

        # Iterate over each image ID and delete related information
        n_image_ids = len(image_ids)
        timer.reset()
        

        if not delete_images:
            logger.info("Iterating over %d images to delete measurements and images", n_image_ids)
        else:
            logger.info("Iterating over %d images to unlink run - delete_images=False so not deleting", n_image_ids)
        for image_id_tuple in image_ids:
            image_id = image_id_tuple[0]
            
            # Check if the Image is associated with more than one run
            sql_cmd = f"SELECT COUNT(*) FROM vast_pipeline_image_run WHERE image_id={image_id};"
            _run_raw_sql(sql_cmd, cursor)
            num_occurences = cursor.fetchone()[0]
            
            # Delete the link between the run and the image
            sql_cmd = f"DELETE FROM vast_pipeline_image_run WHERE image_id = {image_id} AND run_id = {p_run_id};"
            _run_raw_sql(sql_cmd, cursor)
            
            # If the image is associated with more than one run, do not delete the image.
            if num_occurences > 1:
                logger.debug("image_id %d is referenced by %d other pipeline runs, not deleting", image_id, num_occurences-1)
                continue
            elif not delete_images:
                continue

            try:
                sql_cmd = f"DELETE FROM vast_pipeline_measurement WHERE image_id = {image_id};"
                _run_raw_sql(sql_cmd, cursor)
            except Exception as e:
                logger.error("%s %d", e, image_id)
                pass

            try:
                sql_cmd = f"DELETE FROM vast_pipeline_image WHERE id = {image_id};"
                _run_raw_sql(sql_cmd, cursor)
            except Exception as e:
                logger.error("%s %d", e, image_id)
                pass
        t = timer.reset()
        logger.info("Time to iterate over %d image ids: %f seconds", n_image_ids, t)

        # Fetch skyregion IDs associated with the pipeline run
        sql_cmd = f"SELECT skyregion_id FROM vast_pipeline_skyregion_run WHERE run_id = {p_run_id};"
        _run_raw_sql(sql_cmd, cursor, debug=True)
        sky_ids = cursor.fetchall()

        # Iterate over each skyregion ID and delete related information
        n_sky_ids = len(sky_ids)
        logger.info("Iterating over %d skyregion IDs to delete skyregions", n_sky_ids)
        timer.reset()
        for sky_id_tuple in sky_ids:
            sky_id = sky_id_tuple[0]
            
            # Check if the Image is associated with more than one run
            sql_cmd = f"SELECT COUNT(*) FROM vast_pipeline_skyregion_run WHERE skyregion_id={sky_id};"
            _run_raw_sql(sql_cmd, cursor)
            num_occurences = cursor.fetchone()[0]
            
            sql_cmd = f"DELETE FROM vast_pipeline_skyregion_run WHERE skyregion_id = {sky_id} AND run_id = {p_run_id};"
            _run_raw_sql(sql_cmd, cursor)
            
            # If the skyregion is associated with more than one run, do not delete the skyregion.
            if num_occurences > 1:
                logger.debug("skyregion_id %d is referenced by %d other pipeline runs, not deleting", image_id, num_occurences-1)
                continue
            
            try:
                sql_cmd = f"DELETE FROM vast_pipeline_skyregion WHERE id = {sky_id};"
                _run_raw_sql(sql_cmd, cursor)
            except Exception as e:
                logger.error("%s %d", e, sky_id)
                pass
        t = timer.reset()
        logger.info("Time to iterate over %d sky ids: %f seconds", n_sky_ids, t)

        # Finally delete the pipeline run
        sql_cmd = f"DELETE FROM vast_pipeline_run WHERE id = {p_run_id};"
        _run_raw_sql(sql_cmd, cursor)
