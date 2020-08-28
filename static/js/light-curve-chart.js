// Set new default font family and font color to mimic Bootstrap's default styling
Chart.defaults.global.defaultFontFamily = 'Nunito', '-apple-system,system-ui,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif';
Chart.defaults.global.defaultFontColor = '#858796';

// Area Chart Example
var ctx = document.getElementById("lightCurveChart").getContext('2d');
let dataConf = JSON.parse(document.getElementById('chart-data').textContent);
let data = [];
let data_f = [];
let labels = [];
let errors = {};
let errors_f = {};
let max_values = [];
let min_values = [];
dataConf.dataQuery.forEach( function(obj) {
  let dtObj = new Date(obj.datetime);
  let dtObjString = dtObj.toISOString();
  let err = obj.flux_int_err.toFixed(3);
  let flux = obj.flux_int.toFixed(3);
  labels.push(dtObjString);
  max_values.push(parseFloat(flux) + parseFloat(err));
  min_values.push(parseFloat(flux) - parseFloat(err));
  if (obj.forced == true) {
      data.push({x: dtObj, y: null});
      data_f.push({x: dtObj, y: flux});
      errors[dtObjString] = {plus: null, minus: null};
      errors_f[dtObjString] = {plus: err, minus: -err};
  } else {
      data.push({x: dtObj, y: flux});
      data_f.push({x: dtObj, y: null});
      errors[dtObjString] = {plus: err, minus: -err};
      errors_f[dtObjString] = {plus: null, minus: null};
  }
});
let max_max_value = Math.max.apply(null, max_values)
let ymax = max_max_value * 1.05;
let ymin = Math.min.apply(null, min_values) - (ymax - max_max_value);
if (ymin > 0) {
    ymin = 0
}
let conf = {
  type: 'line',
  data: {
    labels: labels,
    datasets: [{
      label: "Measured Flux",
      fill: false,
      showLine: false,
      backgroundColor: "rgba(78, 115, 223, 0.05)",
      borderColor: "rgba(78, 115, 223, 1)",
      pointRadius: 5,
      pointBackgroundColor: "rgba(78, 115, 223, 1)",
      pointBorderColor: "rgba(78, 115, 223, 1)",
      pointHoverRadius: 5,
      pointHoverBackgroundColor: "rgba(78, 115, 223, 1)",
      pointHoverBorderColor: "rgba(78, 115, 223, 1)",
      pointHitRadius: 10,
      pointBorderWidth: 2,
      data: data,
      errorBars: errors,
    },{
      label: "Forced Flux",
      fill: false,
      showLine: false,
      backgroundColor: "rgba(78, 115, 223, 0.05)",
      borderColor: "rgba(78, 115, 223, 1)",
      pointRadius: 5,
      pointBackgroundColor: "rgba(78, 115, 223, 1)",
      pointBorderColor: "rgba(78, 115, 223, 1)",
      pointHoverRadius: 5,
      pointHoverBackgroundColor: "rgba(78, 115, 223, 1)",
      pointHoverBorderColor: "rgba(78, 115, 223, 1)",
      pointHitRadius: 10,
      pointBorderWidth: 2,
      pointStyle: 'triangle',
      data: data_f,
      errorBars: errors_f,
      rotation: 60,
    }],
  },
  options: {
    maintainAspectRatio: false,
    responsive: true,
    layout: {
      padding: {
        left: 10,
        right: 25,
        top: 5,
        bottom: 0,
      }
    },
    plugins:{
      chartJsPluginErrorBars: {
        width: 15 | '10px' | '60%',
      }
    },
    scales: {
      xAxes: [{
        type: 'time',
        distribution: 'linear',
        gridLines: {
          display: false,
          drawBorder: false,
        },
        ticks: {
          maxTicksLimit: 7,
        }
      }],
      yAxes: [{
        scaleLabel: {
          display: true,
          labelString: 'Int. Flux (mJy)',
        },
        ticks: {
          maxTicksLimit: 5,
          padding: 10,
          max: ymax,
          min: ymin,
        },
        gridLines: {
          color: "rgb(234, 236, 244)",
          zeroLineColor: "rgb(234, 236, 244)",
          drawBorder: false,
          borderDash: [2],
          zeroLineBorderDash: [2],
        }
      }],
    },
    legend: {
      // need to sort out axis scaling to turn on
      display: true,
      align: 'end',
      labels: {
        usePointStyle: true,
      },

    },
    tooltips: {
      backgroundColor: "rgb(255,255,255)",
      bodyFontColor: "#858796",
      titleMarginBottom: 10,
      titleFontColor: '#6e707e',
      titleFontSize: 14,
      borderColor: '#dddfeb',
      borderWidth: 1,
      xPadding: 15,
      yPadding: 15,
      displayColors: false,
      intersect: false,
      mode: 'index',
      caretPadding: 10,
      callbacks: {
        label: function(tooltipItem, chart) {
          let datasetLabel = chart.datasets[tooltipItem.datasetIndex].label || '';
          return datasetLabel + ': ' + tooltipItem.yLabel + ' mJy';
        }
      }
    }
  }
};
// fix scale max and min for 1 datapoint
if (labels.length < 2) {
  conf.options.scales.yAxes.forEach(function(obj){
  if (obj.hasOwnProperty('ticks')) {
    obj.ticks['suggestedMin'] = data[0].y - 5;
    obj.ticks['suggestedMax'] = data[0].y + 5;
  }});
};
var myLineChart = new Chart(ctx, conf);
