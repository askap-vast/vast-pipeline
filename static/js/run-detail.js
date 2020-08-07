$(document).ready(function() {

  $('#feedbackModal').on('show.bs.modal', function(e) {
    let apiUrl = document.getElementById('runDetailScript').getAttribute('apiUrl');
    $.ajax({
    type: "GET",
      url: apiUrl,
      success: function(result) {
        $('#feedbackModal .modal-body').html(result.message.text.join('<br>'));
      },
      error: function(result) {
        let resp = result.responseJSON;
        $('#feedbackModal .modal-body').html(resp.message.text.join('<br>'));
      }
    });
  });

});
