/**
 * results.js — Fetch, filter, display, and edit questions on the results page.
 */
document.addEventListener('DOMContentLoaded', () => {
    const listEl = document.getElementById('questionList');
    const countEl = document.getElementById('questionCount');
    const searchInput = document.getElementById('searchInput');
    const filterType = document.getElementById('filterType');
    const filterDiff = document.getElementById('filterDifficulty');
    const filterBloom = document.getElementById('filterBloom');

    let allQuestions = [];

    // Fetch questions
    function fetchQuestions() {
        const params = new URLSearchParams();
        if (filterType.value) params.set('type', filterType.value);
        if (filterDiff.value) params.set('difficulty', filterDiff.value);
        if (filterBloom.value) params.set('bloom', filterBloom.value);
        if (searchInput.value.trim()) params.set('search', searchInput.value.trim());

        fetch(`/api/questions/${DOC_ID}?${params}`)
            .then(r => r.json())
            .then(data => {
                allQuestions = data.questions || [];
                renderQuestions(allQuestions);
            })
            .catch(() => {
                listEl.innerHTML = '<div class="text-center py-5 text-danger">Failed to load questions.</div>';
            });
    }

    // Render
    function renderQuestions(questions) {
        countEl.textContent = `${questions.length} question${questions.length !== 1 ? 's' : ''} found`;

        if (!questions.length) {
            listEl.innerHTML = '<div class="text-center py-5 text-secondary">No questions match your filters.</div>';
            return;
        }

        let html = '';
        questions.forEach((q, i) => {
            const qText = q.question_text || q.question || '';
            const answer = q.answer || '';
            const qType = q.question_type || 'short_answer';
            const diff = q.difficulty || 'medium';
            const bloom = q.bloom_taxonomy || 'remember';
            const qId = q.id || '';

            const typeBadge = {
                fill_blank: '<span class="badge-custom badge-type-fill">Fill Blank</span>',
                wh: '<span class="badge-custom badge-type-wh">WH</span>',
                short_answer: '<span class="badge-custom badge-type-short">Short Answer</span>',
                mcq: '<span class="badge-custom badge-type-mcq">MCQ</span>',
            }[qType] || '<span class="badge-custom badge-type-short">Other</span>';

            const diffBadge = `<span class="badge-custom badge-${diff}">${capitalize(diff)}</span>`;
            const bloomBadge = `<span class="badge-custom badge-${bloom}">${capitalize(bloom)}</span>`;

            let optionsHtml = '';
            if (qType === 'mcq') {
                let options = q.options || [];
                if (typeof options === 'string') try { options = JSON.parse(options); } catch(e) { options = []; }
                const correctIdx = q.correct_index != null ? q.correct_index : -1;
                if (options.length) {
                    optionsHtml = '<ul class="mcq-options">';
                    options.forEach((opt, oi) => {
                        const letter = String.fromCharCode(65 + oi);
                        const isCorrect = oi === correctIdx ? ' correct' : '';
                        optionsHtml += `<li class="mcq-option${isCorrect}">
                            <span class="mcq-option-letter">${letter})</span> ${escapeHtml(opt)}
                            ${isCorrect ? '<i class="bi bi-check-circle-fill text-success ms-auto"></i>' : ''}
                        </li>`;
                    });
                    optionsHtml += '</ul>';
                }
            }

            html += `
            <div class="question-card fade-in" data-id="${qId}">
                <div class="question-header">
                    <span class="question-number">Q${i + 1}</span>
                    ${typeBadge} ${diffBadge} ${bloomBadge}
                    <button class="btn-outline-glass btn-sm ms-auto edit-btn" onclick="toggleEdit(this, '${qId}')"
                            style="font-size:0.8rem;padding:0.25rem 0.6rem;">
                        <i class="bi bi-pencil"></i> Edit
                    </button>
                </div>
                <div class="question-text" data-qid="${qId}">${escapeHtml(qText)}</div>
                ${optionsHtml}
                <div class="question-answer">
                    <strong>Answer:</strong> ${escapeHtml(answer)}
                </div>
                ${q.source_sentence ? `<div class="mt-2" style="font-size:0.8rem;color:var(--text-muted);">
                    <i class="bi bi-quote"></i> ${escapeHtml(q.source_sentence).substring(0, 120)}...
                </div>` : ''}
            </div>`;
        });

        listEl.innerHTML = html;
    }

    // Toggle edit
    window.toggleEdit = function(btn, qId) {
        const card = btn.closest('.question-card');
        const textEl = card.querySelector('.question-text');
        const isEditing = textEl.contentEditable === 'true';

        if (isEditing) {
            // Save
            textEl.contentEditable = 'false';
            btn.innerHTML = '<i class="bi bi-pencil"></i> Edit';
            const newText = textEl.textContent.trim();

            fetch(`/api/questions/${qId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question_text: newText }),
            }).then(r => r.json()).then(data => {
                if (data.success) {
                    btn.innerHTML = '<i class="bi bi-check-lg"></i> Saved';
                    setTimeout(() => { btn.innerHTML = '<i class="bi bi-pencil"></i> Edit'; }, 2000);
                }
            });
        } else {
            textEl.contentEditable = 'true';
            textEl.focus();
            btn.innerHTML = '<i class="bi bi-check-lg"></i> Save';
        }
    };

    // Debounced search
    let searchTimer;
    searchInput.addEventListener('input', () => {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(fetchQuestions, 400);
    });

    [filterType, filterDiff, filterBloom].forEach(el => {
        el.addEventListener('change', fetchQuestions);
    });

    function capitalize(s) { return s.charAt(0).toUpperCase() + s.slice(1); }
    function escapeHtml(s) {
        const d = document.createElement('div');
        d.textContent = s;
        return d.innerHTML;
    }

    fetchQuestions();
});
