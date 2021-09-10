# Pipeline Run Pages

This page details the website pages for information on the pipeline runs.

## List of Pipeline Runs

A list of the pipeline runs that have been processed or initialised are presented on this page along with basic statistics, including the run status.
From this page the full detail page of a specific pipeline run can be accessed by clicking on the name of the pipeline run. 
Explanation of the table options can be found in the [DataTables section](datatables.md).

![!Pipeline Runs table.](../img/pipeline-runs.png){: loading=lazy }

| **Run Status**   | **Description**                                                                  |
| ---------------- | -------------------------------------------------------------------------------- | 
| **Completed**    | The run has successfully finished processing.                                    |
| **Deleting**     | The pipeline run is currently being deleted.                                     | 
| **Error**        | The run has encountered an error during processing and has stopped.              | 
| **Initialised**  | The run has been created but not yet run.                                        | 
| **Queued**       | The run has been sent to the scheduler for running but has not started yet.      | 
| **Restoring**    | The pipeline run is currently being restored.                                    | 
| **Running**      | The run is currently processing.                                                 | 

## Pipeline Run Detail Page

This page presents all the information about the pipeline run, including options to edit the configuration file and to schedule the run for processing, restore the run, delete the run and generate the arrow measurement files.

![!Pipeline Run detail page.](../img/run-detail1.png){: loading=lazy }

### Action Buttons

![!Pipeline Run action buttons.](../img/action-buttons.png){: loading=lazy }

For admins and creators of runs there are four action buttons available:

* **Generate Arrow Files**  
     A process to generate the arrow measurement files.
     See [Generating Arrow Files](../../using/genarrow).
* **Delete Run**  
     Delete the pipeline run.
     See [Deleting a Run](../../using/deleterun).
* **Restore Run**  
     A process to restore the run to the previous successful state.
     See [Restoring a Run](../../using/restorerun).
* **Add Images or Re-Process Run/Process Run**  
     Process the pipeline run.
     See [Processing a Run](../../using/processrun).

### Summary Cards
The cards at the top of the page give a summary of the total numbers of:

* Images in the pipeline run.
* Measurements in the pipeline run.
* Sources in the pipeline run.
* New sources in the pipeline run.

Clicking on the total number of images or measurements will navigate the user to the [Image and Measurements tables](#image-and-measurements-tables) on this page, 
where as the source cards will take the user to the [Sources Query](sourcepages.md#source-query-page) page.

!!! warning
    When sent to the source query page, the user should make sure to click submit on the search.

### Details

A text representation of details of the pipeline run.

### Run Sky Regions

A sky map showing the area of sky covered by the images associated with the pipeline run.

### Configuration File

![!Pipeline Run detail page.](../img/run-detail2.png){: loading=lazy }

Here the pipeline run configuration file can be viewed, edited and validated.

#### Editing the Configuration File

![!Pipeline Run detail page.](../img/run-detail3.png){: loading=lazy align=right width=350px}

To edit the configuration file first select the `Toggle on/off Config Edit` option, that is shown in the screenshot to the right. 
This will enter edit mode on the configuration file as denoted by the `--Edit Mode--` message shown in the screenshot below. 

!!! warning
    Do not toggle off edit mode without first selecting `Wrtie Current Config` otherwise changes will be lost.

![!VAST Pipeline Run Detail](../img/run-detail6.png){: loading=lazy }

When all changes are applied, select the `Write Current Config` to save the changes.

#### Validating the Configuration File

From the configuration file menu select the `Validate Config` option. 
A feedback modal will then appear with feedback stating whether the configuration validation was successful or failed.
The feedback may take a moment to appear as the check is performed.

![!Configuration is valid confirmation.](../img/run-detail7.png){: loading=lazy }

### User Comments

Users are able to read and post comments on a pipeline run using this form.

### Log Files

There are three log files available, which are present depending on the actions performed.

#### Run Log File

The full log file of the pipeline run process.
Will display `N/A` if the run has not been processed.

![!Run log file.](../img/run-detail4.png){: loading=lazy }

#### Restore Log File

The log file of the restore run action. 
Will display `N/A` if the action has not been performed.

![!Restore log file.](../img/run-detail8.png){: loading=lazy }

#### Generate Arrow Files Log File

The log file of the generate arrow files action.
Will display `N/A` if the action has not been performed.

![!Generate arrow files log file.](../img/run-detail9.png){: loading=lazy }


### Image and Measurements Tables

Two tables are on the pipeline run detail page displaying the images and measurements (including forced measurements) that are part of the pipeline run.
