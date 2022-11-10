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

// Issues count graph
function generateIssueCountGraphData(metaId) {
    jsonString = $(`#${metaId}`).attr("content")
    jsonData   = JSON.parse(jsonString);

    chartData = []
    for (const [class_name, count] of Object.entries(jsonData)) {
        chartData.push({
            "class_name": class_name,
            "count": count
        });
    }

    return chartData;
}

function generateIssueCountGraph(chartId, chartData) {

    var chart = am4core.create(chartId, am4charts.PieChart);
    chart.data = chartData;

    if (chart.logo)
        chart.logo.disabled = true
    
    var pieSeries = chart.series.push(new am4charts.PieSeries());
    pieSeries.dataFields.value = "count";
    pieSeries.dataFields.category = "class_name";
    chart.innerRadius = am4core.percent(40);
    chart.legend = new am4charts.Legend();
    chart.hideCredits = true

    chart.legend = new am4charts.Legend();
    
    chart.cursor = new am4charts.XYCursor();

}

// Evolution issues count over time
function generateHistoricIssueEvolutionData(metaId) {
    
    let jsonString = $(`#${metaId}`).attr("content");
    console.log(jsonString)
    let jsonData   = JSON.parse(jsonString);
    console.log(jsonData)
    let chartData  = []   
    let labels     = [ "crack", "moisture", "hot leak", "cold leak" ];

    for (let data of jsonData) {

        const el = { ...data };

        const day   = data.date.slice(0,2);
        const month = data.date.slice(3,5);
        const year  = data.date.slice(6,10);
        el.date = new Date(year, month, day);

        for (let label of labels) {
            if (!(label in data)) {
                el[label] = 0;
            }
        }

        chartData.push(el)
    }

    console.log(chartData)

    return {chartData, labels};
}

function generateHistoricIssueEvolutionGraph(metaId, chartData, labels) {

    var chart = am4core.create(metaId, am4charts.XYChart);
    chart.paddingRight = 35;
    chart.paddingLeft = 35;
    chart.data = chartData;

    // Create axes
    var dateAxis = chart.xAxes.push(new am4charts.DateAxis());
    dateAxis.renderer.minGridDistance = 50;
    dateAxis.renderer.grid.template.location = 0.5;
    dateAxis.startLocation = 0.5;
    dateAxis.endLocation = 0.5;

    // Create value axis
    var valueAxis = chart.yAxes.push(new am4charts.ValueAxis());

    // Create series
    for (let label of labels) {
        var serie = chart.series.push(new am4charts.LineSeries());
        serie.name = label;
        serie.dataFields.valueY = label;
        serie.dataFields.dateX = "date";
        serie.strokeWidth = 3;
        serie.tensionX = 0.8;
        serie.bullets.push(new am4charts.CircleBullet());
        serie.connect = false;
        serie.tooltipText = label + ": [bold]{valueY}[/]";
    }

    chart.legend = new am4charts.Legend();
    
    chart.cursor = new am4charts.XYCursor();
}

// Modal
function showModal(jqueryModal) {
    (new bootstrap.Modal(jqueryModal)) .show()
} 

$(document).ready(() => {

    // Time select 
    $("#report-date-select").on("change", function () {
        window.location = $(this).val();
    })

    // Switch camera fixed button
    normalCamera = true;
    $("#switch-camera-fixed-btn").on("click", function() {
        normalCamera = !normalCamera;
        if (normalCamera) {
            $(".normal-image").removeClass("d-none")
            $(".thermal-image").addClass("d-none")
        } else {
            $(".thermal-image").removeClass("d-none")
            $(".normal-image").addClass("d-none")
        }
    })

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

    // Table line click
    $("#analysis-table-tbody tr").on("click", function() {

        const building_name = $(this).attr("building_name");
        const row           = $(this).attr("building_row");
        const column        = $(this).attr("building_column");

        fetch(`/historic-report/${building_name}/${row}/${column}`)
            .then(response => response.text())
            .then((html) => {

                const modal = $("#historic-analysis-comparison-modal");
                const modalBody = modal.find("#historic-analysis-comparison-modal-body");
                modalBody.empty();
                modalBody.append(html);

                let { chartData, labels } = generateHistoricIssueEvolutionData("historic-analysis-graph-data");
                generateHistoricIssueEvolutionGraph("historic-analysis-graph", chartData, labels);

                showModal(modal);
            })
            .catch(console.error)
        // 
    });

    // count issues graph
    const chartData = generateIssueCountGraphData("report-issues-count-data");
    generateIssueCountGraph("report-issues-count-chart", chartData);
});