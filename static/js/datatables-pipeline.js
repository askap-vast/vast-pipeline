// Call the dataTables jQuery plugin
$(document).ready(function() {
  let dataConf = JSON.parse(document.getElementById('datatable-conf').textContent);
  let testFields = dataConf.colsFields;
  testFields.forEach( function(obj) {
    if (obj.hasOwnProperty('render')) {
      let [prefix, col] = [obj.render.prefix, obj.render.col];
      let hrefValue = function(data, type, row, meta) {
        return '<a href="' + prefix + row.id + '"target=_blank">' + row[col] + '</a>';
      };
      obj.render = hrefValue;
    }
  });
  const dataTableConf = {
    bFilter: dataConf.search,
    hover: true,
    serverSide: true,
    ajax: dataConf.api,
    columns: dataConf.colsFields,
  };
  var table = $('#dataTable').DataTable(dataTableConf);
});
