$(document).ready(function() {

  $('[data-toggle="tooltip"]').tooltip();

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
      url: e.currentTarget.getAttribute('rawImgApi'),
      success: function(result) {
        // populate the images and selavy menus
         $.each(result.fits, function (idx, item) {
          $("#imagesFilesDropDown").append('<option title="' + item.title + '" data-tokens="' + item.datatokens + '">' + item.path + '</option>');
          $("#bkgFilesDropDown").append('<option title="' + item.title + '" data-tokens="' + item.datatokens + '">' + item.path + '</option>');
          $("#noiseFilesDropDown").append('<option title="' + item.title + '" data-tokens="' + item.datatokens + '">' + item.path + '</option>');
         });
         $.each(result.selavy, function (idx, item) {
          $("#selavyFilesDropDown").append('<option title="' + item.title + '" data-tokens="' + item.datatokens + '">' + item.path + '</option>');
         });
         // refresh the state of the drop-down menus
         $('#imagesFilesDropDown').selectpicker('refresh');
         $('#selavyFilesDropDown').selectpicker('refresh');
         $('#bkgFilesDropDown').selectpicker('refresh');
         $('#noiseFilesDropDown').selectpicker('refresh');
      },
      error: function(result) {
        alert('unable to retrieve file paths');
      }
    });
  });

  $("#monitorSwitch").on('click', function(e) {
    $("#bkgFilesDropDown").attr('disabled',!this.checked).selectpicker('refresh');
    $("#monitorMinSigmaSelect").prop('readonly',!this.checked);
    $("#monitorEdgeBufferScaleSelect").prop('readonly',!this.checked);
    $("#monitorClusterThresholdSelect").prop('readonly',!this.checked);
    $("#monitorAllowNanSwitch").attr('disabled',!this.checked);
  });

  $("#pipeRunNext").on('click', function(e) {
    let runName = document.getElementById('pipeRunName');
    if (runName.checkValidity()) {
      if (/^[A-Za-z0-9_-]+$/.test(runName.value)) {
        $('#runNameInv1').hide();
        $("#pipeRunConfigForm").show();
        $("#pipeRunBack").show();
        $("#createPipeRun").show();
        $("#pipeRunNext").hide();
        $("#pipeRunDetailsForm").hide();
      } else {
    $('#runNameInv2').show();
  }
    } else {
      $('#runNameInv1').show();
    }
  });

  $("#pipeRunBack").on('click', function(e) {
    $("#pipeRunConfigForm").hide();
    $("#pipeRunBack").hide();
    $("#createPipeRun").hide();
    $("#pipeRunNext").show();
    $("#pipeRunDetailsForm").show();
  });

  $("#pipeRunReset").on('click', function(e) {
    let dropDownMenus = ['#imagesFilesDropDown', '#selavyFilesDropDown', '#bkgFilesDropDown', '#noiseFilesDropDown'];
    $.each(dropDownMenus, function (idx, item) {
      $(item).val('default').selectpicker('refresh');
    });
  });

  $("#associationTypeSelect").change(function (e) {
    let condition = this.value == 'deruiter';
    $("#associationRadiusSelect").prop('readonly', condition);
    $("#associationBeamWidthSelect").prop('readonly', !condition);
    $("#associationDeRuiterSelect").prop('readonly', !condition);
  });

});
