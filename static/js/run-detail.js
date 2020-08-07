$(document).ready(function() {

  $('#feedbackModal').on('show.bs.modal', function(e) {
    let apiUrl = document.getElementById('runDetailScript').getAttribute('apiValidateUrl');
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

  $("#writeConfig").on('click', function(e) {
    let cfg_text = document.getElementById('runConfigText').textContent;
    let apiUrl = document.getElementById('runDetailScript').getAttribute('apiWriteCfgUrl');
    function getCookie(name) {
      let cookieValue = null;
      if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
          const cookie = cookies[i].trim();
          // Does this cookie string begin with the name we want?
          if (cookie.substring(0, name.length + 1) === (name + '=')) {
            cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
            break;
          }
        }
      }
      return cookieValue;
    };
    const csrftoken = getCookie('csrftoken');
    function csrfSafeMethod(method) {
      // these HTTP methods do not require CSRF protection
      return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    };
    $.ajax({
      beforeSend: function(xhr, settings) {
        if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
          xhr.setRequestHeader("X-CSRFToken", csrftoken);
        }
      },
      type: "POST",
      url: apiUrl,
      data: {'config_text': cfg_text},
      success: function(result) {
        // $('#feedbackModal .modal-body').html(result.message.text.join('<br>'));
      },
      error: function(result) {
        let resp = result.responseJSON;
        // $('#feedbackModal .modal-body').html(resp.message.text.join('<br>'));
      }
    });
  });

});
