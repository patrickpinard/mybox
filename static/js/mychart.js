// =========== chart start
    var ctx1 = document.getElementById("Chart1").getContext("2d");
    var chart1 = new Chart(ctx1, {
      // The type of chart we want to create
      type: "line", // also try bar or other graph types

      // The data for our dataset
      data: {
        labels: 
        [{% for item in labels %}
          "{{item}}",
          {% endfor %}],
        // Information about the dataset
        datasets: [
          {
            label: "intérieur",
            backgroundColor: "transparent",
            borderColor: "#2F80ED",
            data: [
              {% for item in inhouse_temp %}
              "{{item}}",
              {% endfor %}
            ],
            pointBackgroundColor: "transparent",
            pointHoverBackgroundColor: "#2F80ED",
            pointBorderColor: "transparent",
            pointHoverBorderColor: "#fff",
            pointHoverBorderWidth: 5,
            pointBorderWidth: 5,
            pointRadius: 8,
            pointHoverRadius: 8,
            order: 1,
          },{
            label: 'extérieur',
            backgroundColor: "transparent",
            borderColor: "#f39c12",
            data: [{% for item in outside_temp %}
              "{{item}}",
              {% endfor %}],
            pointBackgroundColor: "transparent",
            pointHoverBackgroundColor: "#2F80ED",
            pointBorderColor: "transparent",
            pointHoverBorderColor: "#fff",
            pointHoverBorderWidth: 5,
            pointBorderWidth: 5,
            pointRadius: 8,
            pointHoverRadius: 8,
            order: 2,
          },
          {
            label: 'chauffage',
            lineTension: 0,
            steppedLine: true,
            backgroundColor: "transparent",
            borderColor: "#f12b24",
            data: [{% for item in chauffage %}
              "{{item}}",
              {% endfor %}],
            pointBackgroundColor: "transparent",
            pointHoverBackgroundColor: "#2F80ED",
            pointBorderColor: "transparent",
            pointHoverBorderColor: "#fff",
            pointHoverBorderWidth: 5,
            pointBorderWidth: 5,
            pointRadius: 8,
            pointHoverRadius: 8,
            order: 3,
          }
        ],
      },

      // Configuration options
      options: {
        tooltips: {
          callbacks: {
            labelColor: function (tooltipItem, chart) {
              return {
                backgroundColor: "#ffffff",
              };
            },
          },
          intersect: false,
          backgroundColor: "#f9f9f9",
          titleFontColor: "#8F92A1",
          titleFontColor: "#8F92A1",
          titleFontSize: 12,
          bodyFontColor: "#171717",
          bodyFontStyle: "bold",
          bodyFontSize: 16,
          multiKeyBackground: "transparent",
          displayColors: false,
          xPadding: 30,
          yPadding: 10,
          bodyAlign: "center",
          titleAlign: "center",
        },

        title: {
          display: false,
        },
        legend: {
          display: false,
        },

        scales: {
          yAxes: [
            {
              gridLines: {
                display: false,
                drawTicks: false,
                drawBorder: false,
              },
              ticks: {
                padding: 20,
                max: 25,
                min: -5,
              },
            },
          ],
          xAxes: [
            {
              gridLines: {
                drawBorder: false,
                color: "rgba(143, 146, 161, .1)",
                zeroLineColor: "rgba(143, 146, 161, .1)",
              },
              ticks: {
                padding: 20,
                maxTicksLimit:20,
              },
            },
          ],
        },
      },
    });
    // =========== end chart 