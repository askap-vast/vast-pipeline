import logging

from django.db import connection
from vast_pipeline.utils.utils import StopWatch

logger = logging.getLogger(__name__)

def _run_raw_sql(command, cursor, debug=False, log=True):
    if log:
        if debug:
            logger.debug("Running %s", command)
        else:
            logger.info("Running %s", command)
    cursor.execute(command)
    
    return

def delete_pipeline_run_raw_sql(p_run):
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
        timer = StopWatch()
        for i, source_id_tuple in enumerate(source_ids):
            source_id = source_id_tuple[0]

            # Delete entries from vast_pipeline_sourcefav for each source_id
            sql_cmd = f"DELETE FROM vast_pipeline_sourcefav WHERE source_id = {source_id};"
            _run_raw_sql(sql_cmd, cursor, log=False)

            # Find source tags related to the source and delete them
            sql_cmd = f"SELECT tagulous_source_tags_id FROM vast_pipeline_source_tags WHERE source_id = {source_id};"
            _run_raw_sql(sql_cmd, cursor, log=False)
            tagulous_source_tags_ids = cursor.fetchall()

            for tagulous_source_tags_id_tuple in tagulous_source_tags_ids:
                tagulous_source_tags_id = tagulous_source_tags_id_tuple[0]
                sql_cmd = f"DELETE FROM vast_pipeline_tagulous_source_tags WHERE id = {tagulous_source_tags_id};"
                _run_raw_sql(sql_cmd, cursor, log=False)

            # Delete from vast_pipeline_source_tags for the source_id
            sql_cmd = f"DELETE FROM vast_pipeline_source_tags WHERE source_id = {source_id};"
            _run_raw_sql(sql_cmd, cursor, log=False)

            # Delete from related source
            sql_cmd = f"DELETE FROM vast_pipeline_relatedsource WHERE from_source_id = {source_id};"
            _run_raw_sql(sql_cmd, cursor, log=False)
            sql_cmd = f"DELETE FROM vast_pipeline_relatedsource WHERE to_source_id = {source_id};"
            _run_raw_sql(sql_cmd, cursor, log=False)

            sql_cmd = f"DELETE FROM vast_pipeline_association WHERE source_id = {source_id};"
            _run_raw_sql(sql_cmd, cursor, log=False)
            
            if i % 1000 == 0:
                logger.info(f"Finished source id {source_id} ({i} of {n_source_ids})")
        logger.info(f"Time to iterate over {n_source_ids} source ids: {timer.reset()} seconds")

        # Delete source
        sql_cmd = f"DELETE FROM vast_pipeline_source WHERE run_id = {p_run_id};"
        _run_raw_sql(sql_cmd, cursor)
        
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
        logger.info(f"Iterating over {n_image_ids} images to delete measurements and images")
        timer.reset()

        for image_id_tuple in image_ids:
            image_id = image_id_tuple[0]
            
            # Check if the Image is associated with more than one run
            sql_cmd = f"SELECT COUNT(*) FROM vast_pipeline_image_run WHERE image_id={image_id};"
            _run_raw_sql(sql_cmd, cursor)
            num_occurences = cursor.fetchone()[0]
            
            # Delete the link between the run and the image
            sql_cmd = f"DELETE FROM vast_pipeline_image_run WHERE image_id = {image_id} AND run_id = {p_run_id};"
            _run_raw_sql(sql_cmd, cursor, log=True)
            
            # If the image is associated with more than one run, do not delete the image.
            if num_occurences > 1:
                logger.debug("image_id %d is referenced by {num_occurences} other pipeline runs, not deleting", image_id)
                continue

            try:
                sql_cmd = f"DELETE FROM vast_pipeline_measurement WHERE image_id = {image_id};"
                _run_raw_sql(sql_cmd, cursor, log=True)
            except Exception as e:
                print("++++++++++++++++++++++++++++++++")
                print(e, image_id)
                print("++++++++++++++++++++++++++++++++")
                pass

            try:
                sql_cmd = f"DELETE FROM vast_pipeline_image WHERE id = {image_id};"
                _run_raw_sql(sql_cmd, cursor, log=True)
            except Exception as e:
                print("++++++++++++++++++++++++++++++++")
                print(e, image_id)
                print("++++++++++++++++++++++++++++++++")
                pass
        logger.info(f"Time to iterate over {n_image_ids} image ids: {timer.reset()} seconds")

        # Fetch skyregion IDs associated with the pipeline run
        sql_cmd = f"SELECT skyregion_id FROM vast_pipeline_skyregion_run WHERE run_id = {p_run_id};"
        _run_raw_sql(sql_cmd, cursor, debug=True)
        sky_ids = cursor.fetchall()

        # Iterate over each skyregion ID and delete related information
        n_sky_ids = len(sky_ids)
        logger.info(f"Iterating over {n_sky_ids} skyregion IDs to delete skyregions")
        timer.reset()
        for sky_id_tuple in sky_ids:
            sky_id = sky_id_tuple[0]
            
            # Check if the Image is associated with more than one run
            sql_cmd = f"SELECT COUNT(*) FROM vast_pipeline_skyregion_run WHERE skyregion_id={sky_id};"
            _run_raw_sql(sql_cmd, cursor)
            num_occurences = cursor.fetchone()[0]
            
            sql_cmd = f"DELETE FROM vast_pipeline_skyregion_run WHERE skyregion_id = {sky_id} AND run_id = {p_run_id};"
            _run_raw_sql(sql_cmd, cursor, log=True)
            
            # If the skyregion is associated with more than one run, do not delete the skyregion.
            if num_occurences > 1:
                logger.debug("skyregion_id %d is referenced by {num_occurences} other pipeline runs, not deleting", image_id)
                continue
            
            try:
                sql_cmd = f"DELETE FROM vast_pipeline_skyregion WHERE id = {sky_id};"
                _run_raw_sql(sql_cmd, cursor, log=True)
            except Exception as e:
                print("++++++++++++++++++++++++++++++++")
                print(e, sky_id)
                print("++++++++++++++++++++++++++++++++")
                pass
        logger.info(f"Time to iterate over {n_sky_ids} sky ids: {timer.reset()} seconds")

        # Finally delete the pipeline run
        sql_cmd = f"DELETE FROM vast_pipeline_run WHERE id = {p_run_id};"
        _run_raw_sql(sql_cmd, cursor)
