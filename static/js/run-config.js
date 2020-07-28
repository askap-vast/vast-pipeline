$(document).ready(function() {

  $("#RunConfigButton").on('click', function(e) {
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

  $("#monitorSwitch").on('click', function(e) {
    if (this.checked) {
      $("#bkgFilesDropDown").attr('disabled',false).selectpicker('refresh');
      $("#noiseFilesDropDown").attr('disabled',false).selectpicker('refresh');
    } else {
      $("#bkgFilesDropDown").attr('disabled',true).selectpicker('refresh');
      $("#noiseFilesDropDown").attr('disabled',true).selectpicker('refresh');
    };
  });

});
