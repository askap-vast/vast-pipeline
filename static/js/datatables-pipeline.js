// Formatting function for API
function obj_formatter(obj) {
    if (obj.render.hasOwnProperty('url')) {
        let [prefix, col] = [obj.render.url.prefix, obj.render.url.col];
        let hrefValue = function(data, type, row, meta) {
            return '<a href="' + prefix + row.id + ' "target="_blank">' + row[col] + '</a>';
        };
        obj.render = hrefValue;
        return obj;
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
        return obj;
    };
};


// Call the dataTables jQuery plugin
$(document).ready(function() {
  let dataConf = JSON.parse(document.getElementById('datatable-conf').textContent);
  if (dataConf.hasOwnProperty('api')) {
    // build conf for server side datatable
    let testFields = dataConf.colsFields;
    testFields.forEach( function(obj) {
      if (obj.hasOwnProperty('render')) {
          obj = obj_formatter(obj)
      }
    });
    var dataTableConf = {
      bFilter: dataConf.search,
      hover: true,
      serverSide: true,
      ajax: dataConf.api,
      columns: dataConf.colsFields,
      order: dataConf.order,
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
    if (dataConf.table == 'source_detail') {
        dataTableConf.columnDefs = [
            {
                "targets": 0,
                "searchable": true,
                "visible": false
            },
            {
                "targets": 1,
                "data": "name",
                "render": function ( data, type, row, meta ) {
                    return '<a href="/measurements/'+ row[0] + '"target="_blank">' + row[1] + '</a>';
                }
            },
            {
                "targets": 3,
                "data": "image",
                "render": function ( data, type, row, meta ) {
                    return '<a href="/images/'+ row[12] + '"target="_blank">' + row[3] + '</a>';
                }
            },
            {
                "targets": 4,
                "data": "ra",
                "render": function ( data, type, row, meta ) {
                    return row[4].toFixed(4);
                }
            },
            {
                "targets": 5,
                "data": "ra_err",
                "render": function ( data, type, row, meta ) {
                    return (row[5] * 3600.).toFixed(4);
                }
            },
            {
                "targets": 6,
                "data": "dec",
                "render": function ( data, type, row, meta ) {
                    return row[6].toFixed(4);
                }
            },
            {
                "targets": 7,
                "data": "dec_err",
                "render": function ( data, type, row, meta ) {
                    return (row[7] * 3600.).toFixed(4);
                }
            },
            {
                "targets": 8,
                "data": "flux_int",
                "render": function ( data, type, row, meta ) {
                    return (row[8]).toFixed(3);
                }
            },
            {
                "targets": 9,
                "data": "flux_int_err",
                "render": function ( data, type, row, meta ) {
                    return (row[9]).toFixed(3);
                }
            },
            {
                "targets": 10,
                "data": "flux_peak",
                "render": function ( data, type, row, meta ) {
                    return (row[10]).toFixed(3);
                }
            },
            {
                "targets": 11,
                "data": "flux_peak_err",
                "render": function ( data, type, row, meta ) {
                    return (row[11]).toFixed(3);
                }
            },
            {
                "targets": 14,
                "searchable": false,
                "visible": false
            },
        ]
    };
  };
  var table = $('#dataTable').DataTable(dataTableConf);

  // Trigger the update search on the datatable
  $("#catalogSearch").on('click', function(e) {
    let PipeRun = document.getElementById("runSelect");
    let qry_url = dataConf.api;
    if (PipeRun.value != '') {
      qry_url = qry_url + "&run=" + encodeURIComponent(PipeRun.value);
    };
    let coordunits = document.getElementById("coordUnit");
    let objectname = document.getElementById("objectSearch");
    let objectservice = document.getElementById("objectService");
    let radius = document.getElementById("radiusSelect");
    let ra = document.getElementById("raSelect");
    let dec = document.getElementById("decSelect");
    let unit = document.getElementById("radiusUnit");
    // Object search overrules RA and Dec search
    if (objectname.value) {
      qry_url = qry_url + "&objectname=" + encodeURIComponent(objectname.value);
    }
    if (objectservice.value) {
      qry_url = qry_url + "&objectservice=" + objectservice.value;
    }
    if (coordunits.value) {
      qry_url = qry_url + "&coordsys=" + coordunits.value;
    };
    if (radius.value) {
      qry_url = qry_url + "&radius=" + radius.value;
    };
    if (ra.value) {
      qry_url = qry_url + "&ra=" + ra.value;
    };
    if (dec.value) {
      qry_url = qry_url + "&dec=" + dec.value;
    };
    if (unit.value) {
        qry_url = qry_url + "&radiusunit=" + unit.value
    }
    let flux_type = document.getElementById("aveFluxSelect");
    let flux_min = document.getElementById("fluxMinSelect");
    let flux_max = document.getElementById("fluxMaxSelect");
    if (flux_min.value) {
      qry_url = qry_url + "&min_" + flux_type.value + "=" + flux_min.value;
    };
    if (flux_max.value) {
      qry_url = qry_url + "&max_" + flux_type.value + "=" + flux_max.value;
    };
    let var_v_type = document.getElementById("varVMetricSelect");
    let var_v_min = document.getElementById("varVMinSelect");
    let var_v_max = document.getElementById("varVMaxSelect");
    if (var_v_min.value) {
      qry_url = qry_url + "&min_" + var_v_type.value + "=" + var_v_min.value;
    };
    if (var_v_max.value) {
      qry_url = qry_url + "&max_" + var_v_type.value + "=" + var_v_max.value;
    };
    let var_eta_type = document.getElementById("varEtaMetricSelect");
    let var_eta_min = document.getElementById("varEtaMinSelect");
    let var_eta_max = document.getElementById("varEtaMaxSelect");
    if (var_eta_min.value) {
      qry_url = qry_url + "&min_" + var_eta_type.value + "=" + var_eta_min.value;
    };
    if (var_eta_max.value) {
      qry_url = qry_url + "&max_" + var_eta_type.value + "=" + var_eta_max.value;
    };
    let datapts_min = document.getElementById("datapointMinSelect");
    let datapts_max = document.getElementById("datapointMaxSelect");
    if (datapts_min.value) {
      qry_url = qry_url + "&min_measurements=" + datapts_min.value;
    };
    if (datapts_max.value) {
      qry_url = qry_url + "&max_measurements=" + datapts_max.value;
    };
    let compactness_min = document.getElementById("compactnessMinSelect");
    let compactness_max = document.getElementById("compactnessMaxSelect");
    if (compactness_min.value) {
      qry_url = qry_url + "&min_avg_compactness=" + compactness_min.value;
    };
    if (compactness_max.value) {
      qry_url = qry_url + "&max_avg_compactness=" + compactness_max.value;
    };
    let selavy_min = document.getElementById("SelavyMinSelect");
    let selavy_max = document.getElementById("SelavyMaxSelect");
    if (selavy_min.value) {
      qry_url = qry_url + "&min_selavy_measurements=" + selavy_min.value;
    };
    if (selavy_max.value) {
      qry_url = qry_url + "&max_selavy_measurements=" + selavy_max.value;
    };
    let forced_min = document.getElementById("ForcedMinSelect");
    let forced_max = document.getElementById("ForcedMaxSelect");
    if (forced_min.value) {
      qry_url = qry_url + "&min_forced_measurements=" + forced_min.value;
    };
    if (forced_max.value) {
      qry_url = qry_url + "&max_forced_measurements=" + forced_max.value;
    };
    let relations_min = document.getElementById("RelationsMinSelect");
    let relations_max = document.getElementById("RelationsMaxSelect");
    if (relations_min.value) {
      qry_url = qry_url + "&min_relations=" + relations_min.value;
    };
    if (relations_max.value) {
      qry_url = qry_url + "&max_relations=" + relations_max.value;
    };
    let neighbour_min = document.getElementById("NeighbourMinSelect");
    let neighbour_max = document.getElementById("NeighbourMaxSelect");
    if (neighbour_min.value) {
      qry_url = qry_url + "&min_n_neighbour_dist=" + neighbour_min.value;
    };
    if (neighbour_max.value) {
      qry_url = qry_url + "&max_n_neighbour_dist=" + neighbour_max.value;
    };
    let neighbourRadiusUnit = document.getElementById("neighbourRadiusUnit");
    if (neighbourRadiusUnit.value) {
      qry_url = qry_url + "&NeighbourUnit=" + neighbourRadiusUnit.value;
    };
    if (document.getElementById("newSourceSelect").checked) {
      qry_url = qry_url + "&newsrc";
    }
    if (document.getElementById("containsSiblingsSelect").checked) {
      qry_url = qry_url + "&no_siblings";
    }
    let newsigma_min = document.getElementById("NewSigmaMinSelect");
    let newsigma_max = document.getElementById("NewSigmaMaxSelect");
    if (newsigma_min.value) {
      qry_url = qry_url + "&min_new_high_sigma=" + newsigma_min.value;
    };
    if (newsigma_max.value) {
      qry_url = qry_url + "&max_new_high_sigma=" + newsigma_max.value;
    };
    table.ajax.url(qry_url);
    table.ajax.reload();
  });

  // Trigger the search reset on the datatable
  $("#resetSearch").on('click', function(e) {
    $('#runSelect option').prop('selected', function() {
      return this.defaultSelected
    });
    let inputs = [
      'objectSearch', 'fluxMinSelect', 'fluxMaxSelect', 'varVMinSelect', 'varVMaxSelect',
      'varEtaMinSelect', 'varEtaMaxSelect', 'ForcedMinSelect', 'ForcedMaxSelect',
      'raSelect', 'decSelect', 'radiusSelect', 'datapointMinSelect', 'datapointMaxSelect',
      'RelationsMinSelect', 'RelationsMaxSelect', 'SelavyMinSelect', 'SelavyMaxSelect',
      'NewSigmaMinSelect', 'NewSigmaMaxSelect', 'NeighbourMinSelect', 'NeighbourMaxSelect',
      'compactnessMinSelect', 'compactnessMaxSelect',
      ];
    var input;
    for (input of inputs) {
      document.getElementById(input).value = '';
    };
    document.getElementById("newSourceSelect").checked = false;
    document.getElementById("containsSiblingsSelect").checked = false;
    table.ajax.url(dataConf.api);
    table.ajax.reload();
  });

});
