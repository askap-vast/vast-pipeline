// Call the dataTables jQuery plugin
$(document).ready(function() {
  const dataConf = JSON.parse(document.getElementById('datatable-conf').textContent);
  const dataTableConf = {
    bFilter: dataConf.search,
    hover: true,
    serverSide: true,
    ajax: dataConf.api,
    columns: dataConf.colsFields,
  };
  var table = $('#dataTable').DataTable(dataTableConf);
});
