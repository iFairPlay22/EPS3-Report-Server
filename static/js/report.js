// Issues table filter
function showAllRows() {
    $("#analysis-table-tbody tr").each(function() {
        $(this).removeClass("d-none"); 
    });
}

function showOnlySafeRows() {
    $("#analysis-table-tbody tr").each(function() {
        if (isRowSafe($(this))) {
            $(this).removeClass("d-none");
        } else {
            $(this).addClass("d-none");
        }
    });
}

function showOnlyUnsafeRows() {
    $("#analysis-table-tbody tr").each(function() {
        if (!isRowSafe($(this))) {
            $(this).removeClass("d-none");
        } else {
            $(this).addClass("d-none");
        }
    });
}

function isRowSafe(jqueryRow) {
    console.log(jqueryRow.find(".issue_class"))
    return jqueryRow.find(".issue_class").length == 0
}

function showOnlyConcernedRows(class_name) {
    $("#analysis-table-tbody tr").each(function() {
        if (doesRowConcernClassName($(this), class_name)) {
            $(this).removeClass("d-none");
        } else {
            $(this).addClass("d-none");
        }
    });
}

function doesRowConcernClassName(jqueryRow, class_name) {
    concerns = false;
    jqueryRow
        .find(".issue_class")
        .each(function() {
            if ($(this).attr("class_name") == class_name)
                concerns = true;
        })
    return concerns;
}

// Frequency issues graph
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

    if (chart.logo)
        chart.logo.disabled = true
    
    var pieSeries = chart.series.push(new am4charts.PieSeries());
    pieSeries.dataFields.value = "frequency";
    pieSeries.dataFields.category = "class_name";
    chart.innerRadius = am4core.percent(40);
    chart.legend = new am4charts.Legend();
    chart.hideCredits = true

}

$(document).ready(() => {

    // Issues table filter
    $("#report-issue-select").on('change', function() {
        const class_name = this.value;

        if (class_name == "all")
            showAllRows();
        else if (class_name == "nothing")
            showOnlySafeRows();
        else if (class_name == "issue")
            showOnlyUnsafeRows();
        else
            showOnlyConcernedRows(class_name);
    });

    // Download btn
    $("#analysis-table-download-btn").on("click", function () {
        alert("Available soon...");
    })

    // Frequency issues graph
    const chartData = generateGraphData("report-issues-frequency-data");
    generateGraph("report-issues-frequency-chart", chartData);
});