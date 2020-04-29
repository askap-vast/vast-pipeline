// Set new default font family and font color to mimic Bootstrap's default styling
Chart.defaults.global.defaultFontFamily = 'Nunito', '-apple-system,system-ui,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif';
Chart.defaults.global.defaultFontColor = '#858796';

// Area Chart Example
var ctx = document.getElementById("lightCurveChart").getContext('2d');
let dataConf = JSON.parse(document.getElementById('chart-data').textContent);
let data = [];
let labels = [];
let errors = {};
dataConf.dataQuery.forEach( function(obj) {
  let dtObj = new Date(obj.datetime);
  let dtObjString = dtObj.toISOString();
  data.push({x: dtObj, y: obj.flux_int});
  labels.push(dtObjString);
  let err = obj.flux_int_err / 2.;
  errors[dtObjString] = {plus: err, minus: err};
});
let conf = {
  type: 'line',
  data: {
    labels: labels,
    datasets: [{
      label: "Flux",
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
    }],
  },
  options: {
    maintainAspectRatio: false,
    responsive: true,
    layout: {
      padding: {
        left: 10,
        right: 25,
        top: 25,
        bottom: 0
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
          drawBorder: false
        },
        ticks: {
          maxTicksLimit: 7
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
        },
        gridLines: {
          color: "rgb(234, 236, 244)",
          zeroLineColor: "rgb(234, 236, 244)",
          drawBorder: false,
          borderDash: [2],
          zeroLineBorderDash: [2]
        }
      }],
    },
    legend: {
      display: false
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
