// Set new default font family and font color to mimic Bootstrap's default styling
Chart.defaults.global.defaultFontFamily = 'Nunito', '-apple-system,system-ui,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif';
Chart.defaults.global.defaultFontColor = '#858796';

// Area Chart Example
var ctx = document.getElementById("lightCurveChart");
var myLineChart = new Chart(ctx, {
  type: 'line',
  data: {
    // labels: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    datasets: [{
      label: "Flux",
      fill: false,
      lineTension: 0.3,
      backgroundColor: "rgba(78, 115, 223, 0.05)",
      borderColor: "rgba(78, 115, 223, 1)",
      pointRadius: 3,
      pointBackgroundColor: "rgba(78, 115, 223, 1)",
      pointBorderColor: "rgba(78, 115, 223, 1)",
      pointHoverRadius: 3,
      pointHoverBackgroundColor: "rgba(78, 115, 223, 1)",
      pointHoverBorderColor: "rgba(78, 115, 223, 1)",
      pointHitRadius: 10,
      pointBorderWidth: 2,
      data: [
        {
          x: moment("2014-02-27T10:00:00").format('DD-MMM-YYYY'),
          y: 242,
        },
        {
          x: moment("2014-03-05T10:00:00").format('DD-MMM-YYYY'),
          y: 325,
        },
        {
          x: moment("2014-05-01T10:00:00").format('DD-MMM-YYYY'),
          y: 523,
        },
        {
          x: moment("2014-07-11T10:00:00").format('DD-MMM-YYYY'),
          y: 134,
        },
        {
          x: moment("2014-07-23T10:00:00").format('DD-MMM-YYYY'),
          y: 444,
        }
      ],
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
    scales: {
      // xAxes: [{
      //   time: {
      //     unit: 'date'
      //   },
      //   gridLines: {
      //     display: false,
      //     drawBorder: false
      //   },
      //   ticks: {
      //     maxTicksLimit: 7
      //   }
      // }],
      // yAxes: [{
      //   ticks: {
      //     maxTicksLimit: 5,
      //     padding: 10,
      //   },
      //   gridLines: {
      //     color: "rgb(234, 236, 244)",
      //     zeroLineColor: "rgb(234, 236, 244)",
      //     drawBorder: false,
      //     borderDash: [2],
      //     zeroLineBorderDash: [2]
      //   }
      // }],
      x: {
        type: 'time',
        display: true,
        scaleLabel: {
          display: true,
          labelString: 'Date'
        }
      },
      y: {
        display: true,
        scaleLabel: {
          display: true,
          labelString: 'value'
        }
      }
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
    }
  }
});
