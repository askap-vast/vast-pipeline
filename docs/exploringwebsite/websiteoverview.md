# Website Overview

This page gives an overview of the pipeline website, with links to main pages on features where appropriate.

Refer to [Accessing the Pipeline](../using/access.md) for details on how to access the pipeline instance that is hosted by the VAST collaboration.

For admins, refer to the following pages for details of the configuration and set up of the web server: [Configuration](../gettingstarted/configuration.md), [Deployment](../gettingstarted/deployment.md) and [Web App Admin Usage](../adminusage/app.md).

## Homepage

![!VAST Pipeline homepage.](../img/homepage.png){: loading=lazy }

The homepage contains a welcome message and links to popular pages of the list of pipeline runs, the source query page or the list of images.

## Navbar

![!VAST Pipeline navbar.](../img/navbar.png){: loading=lazy align=right width=80px }

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

See the [Source Query](sourcequery.md) section.

Takes the user to the source query page, where users can search for sources by defining a set of thresholds and feature requirements. 
From the results users can also access the detail page for individual sources.

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
