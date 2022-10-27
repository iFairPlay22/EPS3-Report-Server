

$(document).ready(() => {

    $("#buildings-report-tbody tr").on("click", function() {
        window.location = $(this).attr("href");
    })

})

