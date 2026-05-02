/**
 * dashboard.js — Fetch analytics and render Chart.js visualizations.
 */
document.addEventListener('DOMContentLoaded', () => {

    const COLORS = {
        blue: '#3b82f6', purple: '#8b5cf6', cyan: '#06b6d4',
        amber: '#f59e0b', green: '#10b981', rose: '#f43f5e',
    };

    Chart.defaults.color = '#94a3b8';
    Chart.defaults.borderColor = 'rgba(255,255,255,0.06)';

    fetch('/api/analytics')
        .then(r => r.json())
        .then(data => {
            if (data.error) { console.error(data.error); return; }

            // Stats
            document.getElementById('statUploads').textContent = data.total_uploads || 0;
            document.getElementById('statQuestions').textContent = data.total_questions || 0;
            document.getElementById('statAvgTime').textContent = data.avg_processing_time || '—';

            const types = data.type_distribution || {};
            const topType = Object.entries(types).sort((a, b) => b[1] - a[1])[0];
            document.getElementById('statTopType').textContent = topType
                ? topType[0].replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase())
                : '—';

            // Type chart (doughnut)
            const typeLabels = { fill_blank: 'Fill Blank', wh: 'WH', short_answer: 'Short Answer', mcq: 'MCQ' };
            new Chart(document.getElementById('chartType'), {
                type: 'doughnut',
                data: {
                    labels: Object.keys(types).map(k => typeLabels[k] || k),
                    datasets: [{
                        data: Object.values(types),
                        backgroundColor: [COLORS.blue, COLORS.purple, COLORS.cyan, COLORS.amber],
                        borderWidth: 0,
                    }],
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { padding: 15 } } } },
            });

            // Difficulty chart (bar)
            const diffs = data.difficulty_distribution || {};
            new Chart(document.getElementById('chartDifficulty'), {
                type: 'bar',
                data: {
                    labels: ['Easy', 'Medium', 'Hard'],
                    datasets: [{
                        data: [diffs.easy || 0, diffs.medium || 0, diffs.hard || 0],
                        backgroundColor: [COLORS.green, COLORS.amber, COLORS.rose],
                        borderRadius: 8, borderSkipped: false,
                    }],
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } },
                },
            });

            // Bloom chart (radar)
            const tax = data.taxonomy_distribution || {};
            new Chart(document.getElementById('chartBloom'), {
                type: 'radar',
                data: {
                    labels: ['Remember', 'Understand', 'Apply'],
                    datasets: [{
                        data: [tax.remember || 0, tax.understand || 0, tax.apply || 0],
                        backgroundColor: 'rgba(139, 92, 246, 0.15)',
                        borderColor: COLORS.purple,
                        pointBackgroundColor: COLORS.purple,
                        borderWidth: 2,
                    }],
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: { r: { beginAtZero: true, ticks: { stepSize: 1 } } },
                },
            });

            // Recent documents
            const docs = data.recent_documents || [];
            const tbody = document.getElementById('recentDocs');
            if (!docs.length) {
                tbody.innerHTML = '<tr><td colspan="5" class="text-center text-secondary py-4">No documents yet.</td></tr>';
                return;
            }
            tbody.innerHTML = docs.map(d => {
                const statusBadge = d.status === 'completed'
                    ? '<span class="badge-custom badge-easy">Completed</span>'
                    : d.status === 'failed'
                    ? '<span class="badge-custom badge-hard">Failed</span>'
                    : '<span class="badge-custom badge-medium">Processing</span>';
                const size = d.file_size ? (d.file_size / 1024).toFixed(1) + ' KB' : '—';
                return `<tr>
                    <td class="fw-medium">${d.filename || '—'}</td>
                    <td><span class="file-type-badge">.${d.file_type || '?'}</span></td>
                    <td class="text-secondary">${size}</td>
                    <td>${statusBadge}</td>
                    <td>
                        ${d.status === 'completed' ? `<a href="/results/${d.id}" class="btn-outline-glass" style="font-size:0.8rem;padding:0.2rem 0.6rem;">View</a>` : '—'}
                    </td>
                </tr>`;
            }).join('');
        })
        .catch(err => console.error('Dashboard fetch error:', err));
});
