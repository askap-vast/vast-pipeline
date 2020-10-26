// Formatting function for API
function obj_formatter(obj) {
  if (obj.render.hasOwnProperty('url')) {
    let hrefValue = null;
    if (obj.render.url.hasOwnProperty('nested')) {
      let [prefix, col] = [obj.render.url.prefix, obj.render.url.col];
      hrefValue = function(data, type, row, meta) {
        // split the col on the . for nested JSON and build the selection
        let sel = row;
        col.split('.').forEach(item => sel = sel[item]);
        return '<a href="' + prefix + sel.id + ' "target="_blank">' + data + '</a>';
      };
    } else {
      let [prefix, col] = [obj.render.url.prefix, obj.render.url.col];
      hrefValue = function(data, type, row, meta) {
        return '<a href="' + prefix + row.id + ' "target="_blank">' + row[col] + '</a>';
      };
    }
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
  } else if (obj.render.hasOwnProperty('contains_sibl')) {
    let col = obj.render.contains_sibl.col;
    let sibl_bool = function(data, type, row, meta) {
      if (row[col] > 0) {
        return true;
      } else {
        return false;
      }
    };
    obj.render = sibl_bool;
    return obj;
  };
};


// Call the dataTables jQuery plugin
$(document).ready(function() {

  $('[data-toggle="tooltip"]').tooltip();
  let buttons = [
    {extend: 'colvis', className: 'btn-info btn-sm'},
    {extend: 'csv', className: 'btn-info btn-sm'},
    {extend: 'excel', className: 'btn-info btn-sm'}
  ]
  let dom = (
    "<'row'<'col-sm-3'l><'col-sm-6 text-center'B><'col-sm-3'f>>" +
    "<'row'<'col-sm-12'tr>>" +
    "<'row'<'col-sm-5'i><'col-sm-7'p>>"
  )
  let dataConfParsed = JSON.parse(document.getElementById('datatable-conf').textContent);
  let dataConfList = (Array.isArray(dataConfParsed)) ? dataConfParsed : [dataConfParsed];
  for (let dataConf of dataConfList){
    let table_id = (dataConfList.length == 1) ? '#dataTable' : '#' + dataConf.table_id;
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
        searchDelay: 2000,
        dom : dom,
        buttons: buttons
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
      // initialise the datatable configuration
      var dataTableConf = {
        bFilter: dataConf.search,
        hover: true,
        serverSide: false,
        data: dataSet,
        order: dataConf.order,
        dom: dom,
        buttons: buttons
      };
      if (dataConf.table == 'source_detail') {
        let tableElement = document.getElementById(table_id.replace('#', '')),
          meas_url = tableElement.getAttribute('MeasApi'),
          img_url = tableElement.getAttribute('ImgApi');
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
              return '<a href="' + meas_url + row[0] + '"target="_blank">' + row[1] + '</a>';
            }
          },
          {
            "targets": 3,
            "data": "image",
            "render": function ( data, type, row, meta ) {
              return '<a href="' + img_url + row[17] + '"target="_blank">' + row[3] + '</a>';
            }
          },
          {
            "targets": 4,
            "data": "frequency",
            "render": function ( data, type, row, meta ) {
              return row[4].toFixed(2);
            }
          },
          {
            "targets": 5,
            "data": "ra",
            "render": function ( data, type, row, meta ) {
              return row[5].toFixed(4);
            }
          },
          {
            "targets": 6,
            "data": "ra_err",
            "render": function ( data, type, row, meta ) {
                return (row[6] * 3600.).toFixed(4);
            }
          },
          {
            "targets": 7,
            "data": "dec",
            "render": function ( data, type, row, meta ) {
                return row[7].toFixed(4);
            }
          },
          {
            "targets": 8,
            "data": "dec_err",
            "render": function ( data, type, row, meta ) {
                return (row[8] * 3600.).toFixed(4);
            }
          },
          {
            "targets": 9,
            "data": "flux_int",
            "render": function ( data, type, row, meta ) {
                return (row[9]).toFixed(3);
            }
          },
          {
            "targets": 10,
            "data": "flux_int_err",
            "render": function ( data, type, row, meta ) {
                return (row[10]).toFixed(3);
            }
          },
          {
            "targets": 11,
            "data": "flux_peak",
            "render": function ( data, type, row, meta ) {
                return (row[11]).toFixed(3);
            }
          },
          {
            "targets": 12,
            "data": "flux_peak_err",
            "render": function ( data, type, row, meta ) {
                return (row[12]).toFixed(3);
            }
          },
          {
            "targets": 13,
            "data": "local_rms",
            "render": function ( data, type, row, meta ) {
                return (row[13]).toFixed(2);
            }
          },
          {
            "targets": 14,
            "data": "snr",
            "render": function ( data, type, row, meta ) {
                return (row[14]).toFixed(2);
            }
          },
          {
            "targets": 17,
            "searchable": false,
            "visible": false
          }
        ];
      };
    };
    var table = $(table_id).DataTable(dataTableConf);
  }

  // Simbad and NED search results tables
  $('#externalResultsTable')
  /*
    .on("xhr.dt", function(e, settings, json, xhr) {
      console.log(json);
      if (json === null) {
        return true;
      }
    })
    */
    .DataTable({
      "searching": false,
      "pageLength": 5,
      "lengthChange": false,
      // need a different dom for external results table
      "dom": (
        "<'row'<'col-sm-2'l><'col-sm-8 text-center'B><'col-sm-2'f>>" +
        "<'row'<'col-sm-12'tr>>" +
        "<'row'<'col-sm-5'i><'col-sm-7'p>>"
      ),
      "buttons": buttons,
      "order": [[1, "asc"]],
      "columnDefs": [
        {
          "targets": 0,
          "render": function( data, type, row, meta) {
            if (row["database"] === "SIMBAD") {
              return '<a href="http://simbad.u-strasbg.fr/simbad/sim-id?Ident=' + row['object_name'] + '" target="_blank">' + row['object_name'] + '</a> (' + row['database'] + ')'
            } else if (row["database"] == "NED") {
              return '<a href="https://ned.ipac.caltech.edu/byname?objname=' + row['object_name'] + '" target="_blank">' + row['object_name'] + '</a> (' + row['database'] + ')'
            } else {
              return row['object_name'] + ' (' + row['database'] + ')'
            }
          }
        },
        {
          "targets": 1,
          "render": function ( data, type, row, meta ) {
            return row['separation_arcsec'].toFixed(2);
          }
        },
        {
          "targets": 2,
          "render": function ( data, type, row, meta ) {
            if (row['otype_long'] !== "" && row['otype'] !== row['otype_long']) {
              return '<abbr title="' + row['otype_long'] + '">' + row['otype'] + '</abbr>';
            } else {
              return row['otype'];
            }
          }
        }
      ]
    });
  $('#externalResultsTable').DataTable.ext.pager.numbers_length = 3;

  // Trigger the update search on the datatable
  $("#catalogSearch").on('click', function(e) {
    let PipeRun = document.getElementById("runSelect");
    let qry_url = dataConfParsed.api;
    if (PipeRun.value != '') {
      qry_url = qry_url + "&run=" + encodeURIComponent(PipeRun.value);
    };
    let coordframe = document.getElementById("coordFrameSelect");
    let radius = document.getElementById("radiusSelect");
    let coord = document.getElementById("coordInput");
    let unit = document.getElementById("radiusUnit");
    if (coordframe.value) {
      qry_url = qry_url + "&coordsys=" + coordframe.value;
    };
    if (radius.value) {
      qry_url = qry_url + "&radius=" + radius.value;
    };
    if (coord.value) {
      qry_url = qry_url + "&coord=" + encodeURIComponent(coord.value);
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
    let var_vs_max_type = document.getElementById("varMaxVsMetricSelect");
    let var_vs_max_min = document.getElementById("varMaxVsMinSelect");
    let var_vs_max_max = document.getElementById("varMaxVsMaxSelect");
    if (var_vs_max_min.value) {
      qry_url = qry_url + "&min_" + var_vs_max_type.value + "=" + var_vs_max_min.value;
    };
    if (var_vs_max_max.value) {
      qry_url = qry_url + "&max_" + var_vs_max_type.value + "=" + var_vs_max_max.value;
    };
    let var_m_abs_max_type = document.getElementById("varMaxAbsMMetricSelect");
    let var_m_abs_max_min = document.getElementById("varMaxAbsMMinSelect");
    let var_m_abs_max_max = document.getElementById("varMaxAbsMMaxSelect");
    if (var_m_abs_max_min.value) {
      qry_url = qry_url + "&min_" + var_m_abs_max_type.value + "=" + var_m_abs_max_min.value;
    };
    if (var_m_abs_max_max.value) {
      qry_url = qry_url + "&max_" + var_m_abs_max_type.value + "=" + var_m_abs_max_max.value;
    };
    let datapts_min = document.getElementById("datapointMinSelect");
    let datapts_max = document.getElementById("datapointMaxSelect");
    if (datapts_min.value) {
      qry_url = qry_url + "&min_n_meas=" + datapts_min.value;
    };
    if (datapts_max.value) {
      qry_url = qry_url + "&max_n_meas=" + datapts_max.value;
    };
    let compactness_min = document.getElementById("compactnessMinSelect");
    let compactness_max = document.getElementById("compactnessMaxSelect");
    if (compactness_min.value) {
      qry_url = qry_url + "&min_avg_compactness=" + compactness_min.value;
    };
    if (compactness_max.value) {
      qry_url = qry_url + "&max_avg_compactness=" + compactness_max.value;
    };
    let min_snr_min = document.getElementById("MinSnrMinSelect");
    let min_snr_max = document.getElementById("MinSnrMaxSelect");
    if (min_snr_min.value) {
      qry_url = qry_url + "&min_min_snr=" + min_snr_min.value;
    };
    if (min_snr_max.value) {
      qry_url = qry_url + "&max_min_snr=" + min_snr_max.value;
    };
    let max_snr_min = document.getElementById("MaxSnrMinSelect");
    let max_snr_max = document.getElementById("MaxSnrMaxSelect");
    if (max_snr_min.value) {
      qry_url = qry_url + "&min_max_snr=" + max_snr_min.value;
    };
    if (max_snr_max.value) {
      qry_url = qry_url + "&max_max_snr=" + max_snr_max.value;
    };
    let selavy_min = document.getElementById("SelavyMinSelect");
    let selavy_max = document.getElementById("SelavyMaxSelect");
    if (selavy_min.value) {
      qry_url = qry_url + "&min_n_meas_sel=" + selavy_min.value;
    };
    if (selavy_max.value) {
      qry_url = qry_url + "&max_n_meas_sel=" + selavy_max.value;
    };
    let forced_min = document.getElementById("ForcedMinSelect");
    let forced_max = document.getElementById("ForcedMaxSelect");
    if (forced_min.value) {
      qry_url = qry_url + "&min_n_meas_forced=" + forced_min.value;
    };
    if (forced_max.value) {
      qry_url = qry_url + "&max_n_meas_forced=" + forced_max.value;
    };
    let relations_min = document.getElementById("RelationsMinSelect");
    let relations_max = document.getElementById("RelationsMaxSelect");
    if (relations_min.value) {
      qry_url = qry_url + "&min_n_rel=" + relations_min.value;
    };
    if (relations_max.value) {
      qry_url = qry_url + "&max_n_rel=" + relations_max.value;
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
    let source_selection = document.getElementById("sourceSelectionSelect");
    let source_selection_type = document.getElementById("sourceSelectionTypeSelect");
    if (source_selection.value) {
      qry_url = qry_url + "&source_selection=" + source_selection.value;
    };
    if (source_selection_type.value) {
      qry_url = qry_url + "&source_selection_type=" +source_selection_type.value;
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
      'fluxMinSelect', 'fluxMaxSelect', 'varVMinSelect', 'varVMaxSelect',
      'varEtaMinSelect', 'varEtaMaxSelect', 'ForcedMinSelect', 'ForcedMaxSelect',
      'coordInput', 'radiusSelect', 'datapointMinSelect', 'datapointMaxSelect',
      'RelationsMinSelect', 'RelationsMaxSelect', 'SelavyMinSelect', 'SelavyMaxSelect',
      'NewSigmaMinSelect', 'NewSigmaMaxSelect', 'NeighbourMinSelect', 'NeighbourMaxSelect',
      'compactnessMinSelect', 'compactnessMaxSelect', 'objectNameInput', 'MinSnrMinSelect',
      'MinSnrMaxSelect', 'MaxSnrMinSelect', 'MaxSnrMaxSelect', 'sourceSelectionSelect',
      ];
    var input;
    for (input of inputs) {
      document.getElementById(input).value = '';
    };
    document.getElementById("newSourceSelect").checked = false;
    document.getElementById("containsSiblingsSelect").checked = false;
    // clear validation classes
    $("#objectNameInput").removeClass(["is-valid", "is-invalid"]);
    $("#coordInput").removeClass(["is-valid", "is-invalid"]);
    table.ajax.url(dataConfParsed.api);
    table.ajax.reload();
  });

  // Object name resolver
  $("#objectResolveButton").on('click', function (e) {
    e.preventDefault();  // stop page navigation
    let objectNameInput = $('#objectNameInput');
    let objectNameInputValidation = $('#objectNameInputValidation');
    let sesameService = $('input[name="sesameService"]:checked').val();
    let sesameUrl = $('#objectResolveButton').data('sesame-url');
    let coordInput = $('#coordInput');

    // clear any previous validation
    objectNameInput.removeClass(['is-invalid', 'is-valid']);
    objectNameInputValidation.text(null);
    // perform sesame query
    $.get(sesameUrl, {
      object_name: objectNameInput.val(),
      service: sesameService
    }).done(function (data) {
      objectNameInput.addClass('is-valid');
      coordInput.val(data['coord']);
    }).fail(function (jqxhr) {
      let data = jqxhr.responseJSON;
      objectNameInput.addClass('is-invalid');
      coordInput.val(null);
      if ("object_name" in data) {
        objectNameInputValidation.text(data.object_name.join(" "));
      }
    });
  });

  // Coordinate validator
  $("#coordInput").on('blur', function (e) {
    e.preventDefault();
    let coordInput = $('#coordInput');
    let coordString = coordInput.val();
    let coordFrame = $('#coordFrameSelect').val();
    let validatorUrl = coordInput.data('validator-url');
    let coordInputValidation = $('#coordInputValidation');

    // clear any previous validation
    coordInput.removeClass(['is-invalid', 'is-valid']);
    coordInputValidation.text(null);
    $.get(validatorUrl, {
      coord: coordString,
      frame: coordFrame
    }).done(function (data) {
      coordInput.addClass('is-valid');
    }).fail(function (jqxhr) {
      let data = jqxhr.responseJSON;
      coordInput.addClass('is-invalid');
      if ("coord" in data) {
        coordInputValidation.text(data.coord.join(" "));
      }
    });
  });

});
