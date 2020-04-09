// Call the dataTables jQuery plugin
$(document).ready(function() {
  let dataConf = JSON.parse(document.getElementById('datatable-conf').textContent);
  if (dataConf.hasOwnProperty('api')) {
    // build conf for server side datatable
    let testFields = dataConf.colsFields;
    testFields.forEach( function(obj) {
      if (obj.hasOwnProperty('render')) {
          if (obj.render.hasOwnProperty('url')) {
              let [prefix, col] = [obj.render.url.prefix, obj.render.url.col];
              let hrefValue = function(data, type, row, meta) {
                  return '<a href="' + prefix + row.id + '"target=_blank">' + row[col] + '</a>';
              };
              obj.render = hrefValue;
          } else if (obj.render.hasOwnProperty('float')) {
              let [precision, scale, col] = [
                  obj.render.float.precision,
                  obj.render.float.scale,
                  obj.render.float.col
              ];
              let floatFormat = function(data, type, row, meta) {
                  return (row[col] * scale).toFixed(precision);
              };
              obj.render = floatFormat;
              // obj.render = $.fn.dataTable.render.number( ',', '.', precision );
          };
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
      order: dataConf.order,
    };
  };
  var table = $('#dataTable').DataTable(dataTableConf);

  // Trigger the update search on the datatable
  $("#catalogSearch").on('click', function(e) {
    let PipeRun = document.getElementById("runSelect");
    let qry_url = dataConf.api;
    if (PipeRun.value != '') {
      qry_url = qry_url + "&run=" + PipeRun.value;
    };
    let radius = document.getElementById("radiusSelect");
    let ra = document.getElementById("raSelect");
    let dec = document.getElementById("decSelect");
    if (radius.value) {
      qry_url = qry_url + "&radius=" + radius.value;
    };
    if (ra.value) {
      qry_url = qry_url + "&ra=" + ra.value;
    };
    if (dec.value) {
      qry_url = qry_url + "&dec=" + dec.value;
    };
    let flux_type = document.getElementById("aveFluxSelect");
    let flux_min = document.getElementById("fluxMinSelect");
    let flux_max = document.getElementById("fluxMaxSelect");
    if (flux_min.value) {
      qry_url = qry_url + "&min_" + flux_type.value + "=" + flux_min.value;
    };
    if (flux_max.value) {
      qry_url = qry_url + "&max_" + flux_type.value + "=" + flux_max.value;
    };
    let var_type = document.getElementById("varMetricSelect");
    let var_min = document.getElementById("varMinSelect");
    let var_max = document.getElementById("varMaxSelect");
    if (var_min.value) {
      qry_url = qry_url + "&min_" + var_type.value + "=" + var_min.value;
    };
    if (var_max.value) {
      qry_url = qry_url + "&max_" + var_type.value + "=" + var_max.value;
    };
    let datapts = document.getElementById("datapointSelect");
    if (datapts.value) {
      qry_url = qry_url + "&meas=" + datapts.value;
    };
    if (document.getElementById("newSourceSelect").checked) {
      qry_url = qry_url + "&newsrc";
    }
    table.ajax.url(qry_url);
    table.ajax.reload();
  });

  // Trigger the search reset on the datatable
  $("#resetSearch").on('click', function(e) {
    $('#runSelect option').prop('selected', function() {
      return this.defaultSelected
    });
    let inputs = [
      'fluxMinSelect', 'fluxMaxSelect', 'varMinSelect', 'varMaxSelect',
      'raSelect', 'decSelect', 'radiusSelect', 'datapointSelect'
      ];
    for (input of inputs) {
      document.getElementById(input).value = '';
    };
    document.getElementById("newSourceSelect").checked = false;
    table.ajax.url(dataConf.api);
    table.ajax.reload();
  });

});
