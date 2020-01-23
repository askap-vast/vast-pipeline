// Call the dataTables jQuery plugin
$(document).ready(function() {
  let dataConf = JSON.parse(document.getElementById('datatable-conf').textContent);
  if (dataConf.hasOwnProperty('api')) {
    // build conf for server side datatable
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
    var dataTableConf = {
      bFilter: dataConf.search,
      hover: true,
      serverSide: true,
      ajax: dataConf.api,
      columns: dataConf.colsFields,
    };
  } else {
    // expect that there is a 'data' attribute with the data
    // data are in this format
    // let dataSet = [
    // ["Edinburgh", "5421", "2011/04/25"],
    // ["Sydney", "3636", "2002/02/04"],
    // ...
    // ];
    let dataSet = [];
    dataConf.dataQuery.forEach( function(obj) {
      let row = [];
      dataConf.colsFields.forEach(function(elem) {
        row.push(obj[elem])
      })
      dataSet.push(row)
    });
    var dataTableConf = {
      bFilter: dataConf.search,
      hover: true,
      serverSide: false,
      data: dataSet,
    };
  };
  var table = $('#dataTable').DataTable(dataTableConf);
});
