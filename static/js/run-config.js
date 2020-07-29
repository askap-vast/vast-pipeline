$(document).ready(function() {

  $("#newPipeRunButton").on('click', function(e) {
    // hide second part of form
    $("#pipeRunConfigForm").hide();
    $("#createPipeRun").hide();
    $("#pipeRunBack").hide();
    $("#pipeRunDetailsForm").show();
    $("#pipeRunNext").show();
    // issue the request to get list of images and selavy files
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
    $("#bkgFilesDropDown").attr('disabled',!this.checked).selectpicker('refresh');
    $("#noiseFilesDropDown").attr('disabled',!this.checked).selectpicker('refresh');
    $("#monitorMinSigmaSelect").prop('disabled',!this.checked);
    $("#monitorEdgeBufferScaleSelect").prop('disabled',!this.checked);
  });

  $("#pipeRunNext").on('click', function(e) {
    $("#pipeRunConfigForm").show();
    $("#pipeRunBack").show();
    $("#createPipeRun").show();
    $("#pipeRunNext").hide();
    $("#pipeRunDetailsForm").hide();
  });

  $("#pipeRunBack").on('click', function(e) {
    $("#pipeRunConfigForm").hide();
    $("#pipeRunBack").hide();
    $("#createPipeRun").hide();
    $("#pipeRunNext").show();
    $("#pipeRunDetailsForm").show();
  });

});
