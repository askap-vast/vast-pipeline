function add_source_to_favs(e, url) {
  $.post(url, e.serialize(), function(data) {
    if (data.messages) {
      showPopupMessage(data.messages);
    }
    if (data.success) {
      $('#favStarButton').find("i").css({
        "color": "#ffe271"
      });
    };
  });
  $('#starSource').modal('hide');
}

let apiUrl = document.getElementById('SourceFavScript').getAttribute('apiSourceFavUrl');

$(document).on('submit', '#commentStarForm', function(event){
  add_source_to_favs($(this), apiUrl);
  event.preventDefault();
});
