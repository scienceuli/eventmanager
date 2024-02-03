    // $(document).ready(function () {
    $.fn.dataTableExt.afnFiltering.push(
        function (oSettings, aData, iDataIndex) {
            var dateStart = parseDateValue($("#dateStart").val());
            var dateEnd = parseDateValue($("#dateEnd").val());
            // aData represents the table structure as an array of columns, so the script access the date value
            // in the second column of the table via aData[1]
            var evalDate = parseDateValue(aData[1]);
            console.log('evalDate:', evalDate);
            console.log('dateStart:', dateStart);
            console.log('dateEnd:', dateEnd);


            if (evalDate >= dateStart && evalDate <= dateEnd) {
                return true;
            } else {
                return false;
            }

        });

    // Function for converting a dd.mm.yyyy date value into a numeric string for comparison (example 12.08.2024 becomes 20240812
    function parseDateValue(rawDate) {
        var dateArray = rawDate.split(".");
        var parsedDate = dateArray[2] + dateArray[1] + dateArray[0];
        return parsedDate;
    }
    $(function () {
        $.fn.dataTable.moment('DD-MM-YYYY');
        var $dTable = $('#datatable-orders').DataTable({
            dom: 'Bfrtip',
            "ajax": {
                "processing": true,
                "url": "{% url 'reports:get-orders-data' %}",
                "dataSrc": "",
            },
            buttons: [
                'copy', 'csv', 'excel', 'pdf', 'print'
            ],
            "language": {
                "lengthMenu": "Zeige _MENU_ rows pro Seite",
                "zeroRecords": "Keine Datensätze gefunden",
                "info": "Seite _PAGE_ von _PAGES_, _TOTAL_ records",
                "infoEmpty": "Keine Daten vorhanden",
                "infoFiltered": "Gefiltert aus _MAX_ records",
                "paginate": {
                    "first": "Erste",
                    "last": "Letzte",
                    "next": "Nächste",
                    "previous": "Vorherige"
                },
                "search": "Suche:",
            },
            "lengthMenu": [
                [5, 10, 15, -1],
                [5, 10, 15, "Zeige alle"]
            ],
            "columns": [{
                    "data": "id"
                },
                {
                    'data': "date_created",
                    "render": function (data) {
                        if (data === null) return "";
                        return window.moment(data).format('DD.MM.YYYY')
                    }
                },
                {
                    "data": "lastname"
                },
                {
                    "data": "email"
                },
            ],
        });
        // The dataTables plugin creates the filtering and pagination controls for the table dynamically, so these
        // lines will clone the date range controls currently hidden in the baseDateControl div and append them to
        // the feedbackTable_filter block created by dataTables
        // $dateControls= $("#baseDateControl").children("div").clone();
        // $("#feedbackTable_filter").prepend($dateControls);

        // Implements the jQuery UI Datepicker widget on the date controls

        $(function () {
            $(".datepicker").datepicker();
        });

        // Create event listeners that will filter the table whenever the user types in either date range box or
        // changes the value of either box using the Datepicker pop-up calendar
        $("#dateStart").keyup(function () {
            $dTable.fnDraw();
        });
        $("#dateStart").change(function () {
            $dTable.fnDraw();
        });
        $("#dateEnd").keyup(function () {
            $dTable.fnDraw();
        });
        $("#dateEnd").change(function () {
            $dTable.fnDraw();
        });
    });
