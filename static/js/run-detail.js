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

});
