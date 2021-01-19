# Database Schema

This section describes the relationships between the objects/tables stored in the database.

## Django Web App Schema

The following figure shows a detailed schematics of the schema and relationships as well as tables parameters of the Django App.

[![VAST Pipeline Schema](../img/schema.png){: loading=lazy }](../img/schema.png)


## Pipeline Detailed Schema

A details to the pipeline schema is shown below:

[![VAST Pipeline Schema Detail](../img/schema_pipeline.png){: loading=lazy }](../img/schema_pipeline.png)

### Important points

Some of the key points of the above relationship diagram are:

* each image object is indipendent from the others and can belong to multiple pipeline runs to avoid duplication. __An image can belong to multiple pipeline run objects and a run object can have multiple images.__ If a user want to upload an image object with different characteristic (i.e. using a custom source extraction tool), is free to do so but the __image name need to be unique__. So we suggest to assign a custom name to your image files.
* Each image is linked to a set of source measurement objects by means of a foreign key. Therefore those objects can belong to multiple source objects. __A source object can have multiple measurements and a measurements can belong to multiple source objects.__
* The pipeline schema has been mainly designed to allow for completely disjoint run objects so that each users can run their own processing with their specific settings, defined in the configuration file.
