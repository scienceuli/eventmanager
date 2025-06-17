function fetchAndRenderMembers(eventId) {
    const url = `/dashboard/members/?event=${eventId}`;

    fetch(url)
        .then(response => response.json())
        .then(data => {
            const listContainer = document.getElementById('members-list');
            listContainer.innerHTML = ''; // Clear previous results

            if (!data.members.length) {
                listContainer.innerHTML = '<tr><td colspan="4">Keine Teilnehmer gefunden.</td></tr>';
                return;
            }

            data.members.forEach(member => {
                const row = document.createElement('tr');
                const hasInvoice = member.invoice_id !== null;
                row.className = 'p-2 border rounded';
                row.innerHTML = `
                    <td>${member.name}</td>
                    <td>${member.email}</td>
                    <td>${member.event}</td>
                    ${hasInvoice ? `
                    <td>
                        <a class="btn btn-primary" href="/dashboard/invoice/${member.invoice_id}/" target="_blank" rel="noopener noreferrer">
                        Rechnung
                        </a>
                    </td>`: `<td>Keine Rechnung</td>`}
                `;
                listContainer.appendChild(row);
            });
        })
        .catch(error => {
            console.error('Error loading members:', error);
        });
}


$(document).ready(function () {
    $('#event-filter').select2({
        placeholder: 'Veranstaltung suchen...',
        minimumInputLength: 2,
        ajax: {
            url: '/dashboard/event-autocomplete/',
            dataType: 'json',
            delay: 250,
            data: function (params) {
                return {
                    q: params.term // search term
                };
            },
            processResults: function (data) {
                return {
                    results: data.results // must be an array of {id, text}
                };
            }
        }
    });

    $('#event-filter').on('change', function () {
        const selectedEventId = $(this).val();
        fetchAndRenderMembers(selectedEventId);
    });
});