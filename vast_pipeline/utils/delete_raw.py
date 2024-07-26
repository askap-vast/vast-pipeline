from django.db import connection


def delete_pipeline_run_raw_sql(p_run):
    p_run_id = p_run.pk

    with connection.cursor() as cursor:
        # Fetch source IDs associated with the pipeline run
        cursor.execute("SELECT id FROM vast_pipeline_source WHERE run_id = %s;", (p_run_id,))
        source_ids = cursor.fetchall()

        # Iterate over each source ID and delete related information
        for source_id_tuple in source_ids:
            source_id = source_id_tuple[0]

            # Delete entries from vast_pipeline_sourcefav for each source_id
            cursor.execute("DELETE FROM vast_pipeline_sourcefav WHERE source_id = %s;", (source_id,))

            # Find source tags related to the source and delete them
            cursor.execute("SELECT tagulous_source_tags_id FROM vast_pipeline_source_tags WHERE source_id = %s;", (source_id,))
            tagulous_source_tags_ids = cursor.fetchall()

            for tagulous_source_tags_id_tuple in tagulous_source_tags_ids:
                tagulous_source_tags_id = tagulous_source_tags_id_tuple[0]
                cursor.execute("DELETE FROM vast_pipeline_tagulous_source_tags WHERE id = %s;", (tagulous_source_tags_id,))

            # Delete from vast_pipeline_source_tags for the source_id
            cursor.execute("DELETE FROM vast_pipeline_source_tags WHERE source_id = %s;", (source_id,))

            # Delete from related source
            cursor.execute("DELETE FROM vast_pipeline_relatedsource WHERE from_source_id = %s;", (source_id,))
            cursor.execute("DELETE FROM vast_pipeline_relatedsource WHERE to_source_id = %s;", (source_id,))

            cursor.execute("DELETE FROM vast_pipeline_association WHERE source_id = %s;", (source_id,))

        # Delete source
        cursor.execute("DELETE FROM vast_pipeline_source WHERE run_id = %s;", (p_run_id,))

        # Delete comments
        cursor.execute("DELETE FROM vast_pipeline_comment WHERE object_id = %s;", (p_run_id,))

        # Fetch image IDs associated with the pipeline run
        cursor.execute("SELECT image_id FROM vast_pipeline_image_run WHERE run_id = %s;", (p_run_id,))
        image_ids = cursor.fetchall()

        # Iterate over each image ID and delete related information
        for image_id_tuple in image_ids:
            image_id = image_id_tuple[0]
            cursor.execute("DELETE FROM vast_pipeline_measurement WHERE image_id = %s;", (image_id,))
            cursor.execute("DELETE FROM vast_pipeline_image_run WHERE image_id = %s;", (image_id,))
            cursor.execute("DELETE FROM vast_pipeline_image WHERE id = %s;", (image_id,))

        # Fetch skyregion IDs associated with the pipeline run
        cursor.execute("SELECT skyregion_id FROM vast_pipeline_skyregion_run WHERE run_id = %s;", (p_run_id,))
        sky_ids = cursor.fetchall()

        # Iterate over each skyregion ID and delete related information
        for sky_id_tuple in sky_ids:
            sky_id = sky_id_tuple[0]
            cursor.execute("DELETE FROM vast_pipeline_skyregion_run WHERE skyregion_id = %s;", (sky_id,))
            cursor.execute("DELETE FROM vast_pipeline_skyregion WHERE id = %s;", (sky_id,))

        # Finally delete the pipeline run
        cursor.execute("DELETE FROM vast_pipeline_run WHERE id = %s;", (p_run_id,))



