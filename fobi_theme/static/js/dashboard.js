let chart;

function fetchAndRenderChart() {
    const year = document.getElementById('year-filter').value;
    const search = document.getElementById('search-filter').value;
    const metric = document.getElementById('metric-select').value;

    const params = new URLSearchParams();
    if (year) params.append('year', year);
    if (search) params.append('search', search);

    fetch(`/dashboard/stats/?${params.toString()}`)
        .then(res => res.json())
        .then(data => {
            const labels = data.event_data.map(e => e.name);
            const values = data.event_data.map(e => {
                return metric === 'cost' ? (e.costs || 0) : e.num_orders;
            });

            const label = metric === 'cost' ? 'Kosten (€)' : 'Anzahl Teilnehmer';
            const xtitle = metric === 'cost' ? 'Kosten' : 'Teilnehmer';
            const mtitle = metric === 'cost' ? 'Kosten pro Veranstaltung' : 'Teilnehmer pro Veranstaltung';
            const bgcolor = metric === 'cost' ? 'rgba(39, 191, 245, 0.8)' : 'rgba(75, 192, 192, 0.6)';

            if (chart) {

                chart.data.labels = labels;
                chart.data.datasets[0].data = values;
                // chart.data.datasets[0].label = label;
                chart.data.datasets[0].label = metric === 'cost' ? 'Kosten (€)' : 'Anzahl Teilnehmer';
                chart.data.datasets[0].backgroundColor = metric === 'cost' ? 'rgba(39, 191, 245, 0.8)' : 'rgba(75, 192, 192, 0.6)';
                const xtitle = metric === 'cost' ? 'Kosten' : 'Teilnehmer';
                const mtitle = metric === 'cost' ? 'Kosten pro Veranstaltung' : 'Teilnehmer pro Veranstaltung';
                resize(labels.length);
                chart.update();
            } else {
                const ctx = document.getElementById('event-chart').getContext('2d');
                chart = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: label,
                            data: values,
                            backgroundColor: bgcolor
                        }]
                    },
                    options: {
                        indexAxis: 'y',
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                display: false
                            },
                            title: {
                                display: true,
                                text: mtitle
                            }
                        },
                        scales: {
                            x: {
                                beginAtZero: true,
                                title: {
                                    display: true,
                                    text: xtitle
                                }
                            },
                            y: {
                                title: {
                                    display: true,
                                    text: 'Veranst.'
                                }
                            }
                        }
                    }
                });
                resize(labels.length);

            }

            function resize(length) {
                const barHeight = 20;
                let newHeight = barHeight * length;
                if (newHeight < 300) {
                    newHeight = 300;
                }
                chart.canvas.parentNode.style.height = newHeight + 'px';
            }
        });
}




// Bind change events
document.addEventListener('DOMContentLoaded', () => {
    fetchAndRenderChart();

    document.getElementById('year-filter').addEventListener('change', fetchAndRenderChart);
    document.getElementById('search-filter').addEventListener('input', () => {
        clearTimeout(window.searchDebounce);
        window.searchDebounce = setTimeout(fetchAndRenderChart, 300); // debounce
    });
    document.getElementById('metric-select').addEventListener('change', fetchAndRenderChart);

});