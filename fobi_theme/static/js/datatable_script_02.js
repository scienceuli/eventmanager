$(function() {
    // Setup - add a text input to each footer cell
    $('#datatable-orders tfoot th').each( function (i) {
        var title = $('#datatable-orders thead th').eq( $(this).index() ).text();
        $(this).html( '<input type="text" placeholder="'+title+'" data-index="'+i+'" />' );
    } );

    var dTable = $('#datatable-orders').DataTable({
        dom: 'Bfrtip',
        "ajax": {
            "processing": true,
            "url": "/reports/datatable/get_orders_data/",
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
                'type': 'de_date',
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

    // Filter event handler
    $( dTable.table().container() ).on( 'keyup', 'tfoot input', function () {
        dTable
            .column( $(this).data('index') )
            .search( this.value )
            .draw();
    } );
    
  
    $("#datepicker_from").datepicker({
        "dateFormat": "dd.mm.yy",
      "onSelect": function(date) {
        minDateFilter = new Date(parseDateValue(date)).getTime();
        // console.log('date:', date);
        // console.log('Date(date):', new Date(parseDateValue(date)));
        // console.log('minDateFilter:', minDateFilter);
        dTable.draw();
      }
    }).keyup(function() {
      minDateFilter = new Date(parseDateValue(this.value)).getTime();
      dTable.draw();
    });
  
    $("#datepicker_to").datepicker({
      "dateFormat": "dd.mm.yy",
      "onSelect": function(date) {
        maxDateFilter = new Date(parseDateValue(date)).getTime();
        dTable.draw();
      }
    }).keyup(function() {
      maxDateFilter = new Date(parseDateValue(this.value)).getTime();
      dTable.draw();
    });
  
  });
  
  

  // Function for converting a dd.mm.yyyy date value into a numeric string for comparison (example 12.08.2024 becomes 20240812
  function parseDateValue(rawDate) {
    var dateArray = rawDate.split(".");
    var parsedDate = dateArray[2] + '-' + dateArray[1] + '-' + dateArray[0];
    return parsedDate;
    };
    // Date range filter
    minDateFilter = "";
    maxDateFilter = "";
  
  $.fn.dataTableExt.afnFiltering.push(
    function(oSettings, aData, iDataIndex) {
      if (typeof aData._date == 'undefined') {
        console.log(typeof parseDateValue(aData[1]))
        console.log("bsp:", new Date('2015-03-25'));
        aData._date = new Date(parseDateValue(aData[1])).getTime();
        console.log("aData[1]:", parseDateValue(aData[1]));
        console.log('Date(aData):', new Date(parseDateValue(aData[1])));
        console.log('aData._date: ', aData._date);
      }
  
      if (minDateFilter && !isNaN(minDateFilter)) {
        if (aData._date < minDateFilter) {
          return false;
        }
      }
  
      if (maxDateFilter && !isNaN(maxDateFilter)) {
        if (aData._date > maxDateFilter) {
          return false;
        }
      }
  
      return true;
    }
  );