$(document).ready(function() {

    $("#RunConfigButton").on('click', function(e) {
        // e.preventDefault();
        $.ajax({
            type: "GET",
            url: "/api/rawimages/",
            success: function(result) {
                // populate the images and selavy menus
                // console.log(result);
                 $.each(result.fits, function (idx, item) {
                    $("#imagesFilesDropDown").append('<option>' + item + '</option>');
                    $("#bkgFilesDropDown").append('<option>' + item + '</option>');
                    $("#noiseFilesDropDown").append('<option>' + item + '</option>');
                 });
                 $.each(result.selavy, function (idx, item) {
                    $("#selavyFilesDropDown").append('<option>' + item + '</option>');
                 });
                 $('#imagesFilesDropDown').selectpicker('refresh');
                 $('#selavyFilesDropDown').selectpicker('refresh');
                 $('#bkgFilesDropDown').selectpicker('refresh');
                 $('#noiseFilesDropDown').selectpicker('refresh');
            },
            error: function(result) {
                alert('error');
            }
        });
    });

});
