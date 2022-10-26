
function generateGraphData(metaId) {
    jsonString = $(`#${metaId}`).attr("content")
    jsonData   = JSON.parse(jsonString);

    chartData = []
    for (const [class_name, frequency] of Object.entries(jsonData)) {
        chartData.push({
            "class_name": class_name,
            "frequency": frequency
        });
    }

    return chartData;
}

function generateGraph(chartId, chartData) {

    var chart = am4core.create(chartId, am4charts.PieChart);
    chart.data = chartData;
    
    var pieSeries = chart.series.push(new am4charts.PieSeries());
    pieSeries.dataFields.value = "frequency";
    pieSeries.dataFields.category = "class_name";
    chart.innerRadius = am4core.percent(40);
    chart.legend = new am4charts.Legend();
    chart.hideCredits = true

}

$(document).ready(() => {
    const chartData = generateGraphData("report-issues-frequency-data")
    generateGraph("report-issues-frequency-chart", chartData);
});