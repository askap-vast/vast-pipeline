// This function is used by ajax calls to show toast messages
function showPopupMessage(content) {
  var elMessages = $('#messages-list');
  if (elMessages.length && content) {
      elMessages.html(content);
  }
  $(".toast").toast('show');
}

$(document).ready(function() {
    $(".toast").toast('show');
});
