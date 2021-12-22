$(document).ready(function() {

  const PrismHighlight = () => {
    let pre_tag = document.getElementById('runConfigText'),
      code = document.getElementById('runConfigTextCode');
    code.innerHTML = pre_tag.innerText
    pre_tag.innerHTML = code.outerHTML
    Prism.highlightElement(pre_tag.firstChild);
    return pre_tag.innerText;
  };

  $('#editConfig').on('click', function(e) {
    let edit_txt_check = document.getElementById('editModeTitle').hidden;
    $('#editModeTitle').prop('hidden', !edit_txt_check);
    $('#runConfigText').prop('contenteditable', edit_txt_check);
    if (!edit_txt_check) {
      let text = PrismHighlight();
    }
  });

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

  $('#writeConfig').on('click', function(e) {
    e.preventDefault();
    let text = PrismHighlight();
    $('input#configTextInput').val(text);
    document.getElementById('runConfigForm').submit();
  });

  // load logs on page load
  var logfile = document.getElementById('logs').value;
  if (!!logfile) {
    loadlog(logfile, 'runlog');
  }

  var logfile = document.getElementById('restorelogs').value;
  if (!!logfile) {
    loadlog(logfile, 'restorelog');
  }

  var logfile = document.getElementById('genarrowlogs').value;
  if (!!logfile) {
    loadlog(logfile, 'genarrowlog');
  }

  // load logs on selection change
  $('#logs').on('change', function () {
    let logfile = document.getElementById('logs').value;
    loadlog(logfile, 'runlog');
  });

  $('#restorelogs').on('change', function () {
    let logfile = document.getElementById('restorelogs').value;
    loadlog(logfile, 'restorelog');
  });

  $('#genarrowlogs').on('change', function () {
    let logfile = document.getElementById('genarrowlogs').value;
    loadlog(logfile, 'genarrowlog');
  });
});


function loadlog(logfile, type) {
  // Function to load a run log file
  let apiUrl = document.getElementById('runDetailScript').getAttribute('apiRunLogUrl');

  $.ajax({
    type: "GET",
    url: apiUrl + "?logname="+ logfile,
    success: function (data) {
      if (type == 'runlog') {
        $("#logtext").html(data.log_html_content);
      } else if (type == 'restorelog') {
        $("#restorelogtext").html(data.log_html_content);
      } else if (type == 'genarrowlog') {
        $("#genarrowlogtext").html(data.log_html_content);
      }
    }
  });
};