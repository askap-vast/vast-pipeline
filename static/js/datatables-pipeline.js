// Call the dataTables jQuery plugin
$(document).ready(function() {
  $('#dataTable').DataTable({
    "serverSide": true,
    "ajax": "/api/datasets/?format=datatables",
    "columns": [
      {"data": "id"},
      {"data": "name"},
      {"data": "path"},
      {"data": "comment"},
    ]
  });
});
