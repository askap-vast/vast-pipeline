import logging

from django.db import connection
from tqdm import tqdm

logger = logging.getLogger(__name__)

def _run_raw_sql(command, cursor, debug=False, log=True):
    if log:
        log_str = f"Running {command}"
        if debug:
            logger.debug(log_str)
        else:
            logger.info(log_str)
    cursor.execute(command)
    
    return

def delete_pipeline_run_raw_sql(p_run):
    p_run_id = p_run.pk

    with connection.cursor() as cursor:
        # create index
        #sql_cmd = f"CREATE INDEX idx_run_id ON vast_pipeline_source (run_id);"
        #_run_raw_sql(sql_cmd, cursor)
        
        # Disable triggers
        #isql_cmd = "ALTER TABLE vast_pipeline_source DISABLE TRIGGER ALL;"
        #_run_raw_sql(sql_cmd, cursor)
        
        # Fetch source IDs associated with the pipeline run
        sql_cmd = f"SELECT id FROM vast_pipeline_source WHERE run_id = {p_run_id};"
        _run_raw_sql(sql_cmd, cursor)
        source_ids = cursor.fetchall()

        # Iterate over each source ID and delete related information
        logger.info(f"Iterating over {len(source_ids)} sources to delete tags and relations")
        for source_id_tuple in tqdm(source_ids):
            source_id = source_id_tuple[0]

            # Delete entries from vast_pipeline_sourcefav for each source_id
            sql_cmd = f"DELETE FROM vast_pipeline_sourcefav WHERE source_id = {source_id};"
            _run_raw_sql(sql_cmd, cursor, log=True)

            # Find source tags related to the source and delete them
            sql_cmd = f"SELECT tagulous_source_tags_id FROM vast_pipeline_source_tags WHERE source_id = {source_id};"
            _run_raw_sql(sql_cmd, cursor, log=True)
            tagulous_source_tags_ids = cursor.fetchall()

            for tagulous_source_tags_id_tuple in tagulous_source_tags_ids:
                tagulous_source_tags_id = tagulous_source_tags_id_tuple[0]
                sql_cmd = f"DELETE FROM vast_pipeline_tagulous_source_tags WHERE id = {tagulous_source_tags_id};"
                _run_raw_sql(sql_cmd, cursor, log=True)

            # Delete from vast_pipeline_source_tags for the source_id
            sql_cmd = f"DELETE FROM vast_pipeline_source_tags WHERE source_id = {source_id};"
            _run_raw_sql(sql_cmd, cursor, log=True)

            # Delete from related source
            sql_cmd = f"DELETE FROM vast_pipeline_relatedsource WHERE from_source_id = {source_id};"
            _run_raw_sql(sql_cmd, cursor, log=True)
            sql_cmd = f"DELETE FROM vast_pipeline_relatedsource WHERE to_source_id = {source_id};"
            _run_raw_sql(sql_cmd, cursor, log=True)

            sql_cmd = f"DELETE FROM vast_pipeline_association WHERE source_id = {source_id};"
            _run_raw_sql(sql_cmd, cursor, log=True)

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
        logger.info(f"Iterating over {len(image_ids)} images to delete measurements and images")
        for image_id_tuple in tqdm(image_ids):
            image_id = image_id_tuple[0]
            try:
                sql_cmd = f"DELETE FROM vast_pipeline_measurement WHERE image_id = {image_id};"
                _run_raw_sql(sql_cmd, cursor, log=True)
            except Exception as e:
                print("++++++++++++++++++++++++++++++++")
                print(e, image_id)
                print("++++++++++++++++++++++++++++++++")
                pass
            sql_cmd = f"DELETE FROM vast_pipeline_image_run WHERE image_id = {image_id} AND run_id = {p_run_id};"
            _run_raw_sql(sql_cmd, cursor, log=True)
            try:
                sql_cmd = f"DELETE FROM vast_pipeline_image WHERE id = {image_id};"
                _run_raw_sql(sql_cmd, cursor, log=True)
            except Exception as e:
                print("++++++++++++++++++++++++++++++++")
                print(e, image_id)
                print("++++++++++++++++++++++++++++++++")
                pass

        # Fetch skyregion IDs associated with the pipeline run
        sql_cmd = f"SELECT skyregion_id FROM vast_pipeline_skyregion_run WHERE run_id = {p_run_id};"
        _run_raw_sql(sql_cmd, cursor, debug=True)
        sky_ids = cursor.fetchall()

        # Iterate over each skyregion ID and delete related information
        logger.info(f"Iterating over {len(sky_ids)} skyregion IDs to delete skyregions")
        for sky_id_tuple in tqdm(sky_ids):
            sky_id = sky_id_tuple[0]
            sql_cmd = f"DELETE FROM vast_pipeline_skyregion_run WHERE skyregion_id = {sky_id} AND run_id = {p_run_id};"
            _run_raw_sql(sql_cmd, cursor, log=True)
            try:
                sql_cmd = f"DELETE FROM vast_pipeline_skyregion WHERE id = {sky_id};"
                _run_raw_sql(sql_cmd, cursor, log=True)
            except Exception as e:
                print("++++++++++++++++++++++++++++++++")
                print(e, sky_id)
                print("++++++++++++++++++++++++++++++++")
                pass

        # Finally delete the pipeline run
        sql_cmd = f"DELETE FROM vast_pipeline_run WHERE id = {p_run_id};"
        _run_raw_sql(sql_cmd, cursor)



