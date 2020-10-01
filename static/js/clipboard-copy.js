$(function() {
  // append copy icon to each .clipboard-copy element
  $('.clipboard-copy').append('<i class="far fa-copy ml-2" data-toggle="tooltip" data-placement="top"></i>');
  // init the tooltip for the copy icons
  $('i.fa-copy[data-toggle="tooltip"]').tooltip({title: "Copy to clipboard"});
  // perform the copy action and update tooltip title to notify user
  $('.clipboard-copy > i.fa-copy').on("click", function() {
    let data = $(this).parent().text();
    navigator.clipboard.writeText(data);
    $(this).tooltip('dispose').tooltip({"title": "Copied!"}).tooltip('update').tooltip('show');
  })
  // revert copy tooltip title to original on mouseout
  $('.clipboard-copy > i.fa-copy').on("mouseout", function() {
    $(this).tooltip('dispose').tooltip({title: "Copy to clipboard"});
  })
});