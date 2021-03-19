# Website Overview

This page gives an overview of the pipeline website, with links to main pages on features where appropriate.

Refer to [Accessing the Pipeline](../using/access.md) for details on how to access the pipeline instance that is hosted by the VAST collaboration.

For admins, refer to the following pages for details of the configuration and set up of the web server: [Configuration](../quickstart/configuration.md), [Deployment](../quickstart/deployment.md) and [Web App Admin Usage](../adminusage/app.md).

## Homepage

[![VAST Pipeline Homepage](../img/homepage.png){: loading=lazy }](../img/homepage.png)

The homepage provides a summary of the data currently held in the pipeline instance that has been processed. The four cards at the top of the homepage provide total values
for the amount of pipeline runs, images, measurements and sources that are stored in the database. Clicking any of them will take you to the respective overview page for the data type.

!!! note
    The totals presented on the homepage are totals for all pipeline runs combined!

Also displayed is a sky region map that shows all the areas of the sky that have had successful and completed pipeline runs performed.


## Navbar

[![VAST Pipeline Navbar](../img/navbar.png){: loading=lazy align=right width=80px }](../img/navbar.png)

The navbar, shown to the right, acts as the main method in which to navigate around the website.
The following sections link to the respective documentation pages explainging the features of each link.

!!! note
    The admin button on the navbar is only seen when the user is designated as an administrator.

!!! tip
    The navbar can be collapsed by pressing the menu (or hamburger) button next to it at the top of the page.

### Admin

See the [website admin tools](admintools.md) page.

Allows for admins to manage users, Django Q schedules and the data itself.

### Pipeline Runs

See the [Pipeline Run Pages](runpages.md) doc.

Navigates the user to the list of pipeline runs available, which in turn link to the detail page for each respective run.

### Sources Query

See the [Source Pages](sourcepages.md) section.

Takes the user to the source query page, where users can search for sources by defining a set of thresholds and feature requirements. 
From the results users can also access the detail page for individual sources.

### Measurements

See the [Measurement Pages](measurementpages.md) section.

Navigates the user to the measurements page that features a table containing all the measurements currently held in the database. 
From here users can also access the detail page for individual measurements.

### Images

See the [Image Pages](imagepages.md) section.

Takes the user to the images page that features a table containing all the images currently held in the database. 
From here users can also access the detail page for individual images.

### External Links

* **Documentation**: Links to this documentation website.
* **Pipeline Repository**: A link to the GitHub pipeline repository.
* **Raise an Issue**: A link to open a new issue on the GitHub repository.
* **Start a Discussion**: A link to open a new discussion on the GitHub repository.
* **VAST Links**
    - **GitHub**: A link to the VAST organisation GitHub page.
    - **JupyterHub**: Links to the VAST hosted JupyterHub instance which includes access to the pipeline results and `vast-tools`.
    - **Website**: Links to the VAST collaboration website.
    - **Wiki**: Links to the VAST Wiki which is hosted on GitHub.

## Data Tables

Much of the data is presented using tables that share consistent functionality across the website. 
An example of a table is shown below, note the interactive features across the top of the table, these are explained after the screenshot.

[![VAST Pipeline Datatable](../img/datatables.png){: loading=lazy }](../img/datatables.png)

* **Show 10 entries**: A selectable limiter of how many rows to display at once (maximum 100).
* **Column visibility**: Enables the user to hide and show columns columns. In the screenshot below the `compactness` column is hidden by deselecting it in the presented list. 
    [![VAST Pipeline Datatable Column Visibility](../img/datatables-colvis.png){: loading=lazy }](../img/datatables-colvis.png)
* **CSV**: Will download a CSV file of the data currently shown on screen.
* **Excel**: Will download an Excel file of the data currently shown on screen.

    !!! warning
        Note the statement **currently shown on screen** - only this data will be downloaded to the CSV and Excel files. All the records are not able to be downloaded
        in this manner - for this it is recommened to interact with the output [parquet files](../outputs/outputs.md).
        
* **Search**: A search bar for the user to filter the table to the row they require. The search will take into account all appropriate columns when searching.