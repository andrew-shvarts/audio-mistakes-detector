const ERROR_META = {
  missing:     { label: 'Missing',     color: 'var(--c-missing)' },
  duplicate:   { label: 'Duplicate',   color: 'var(--c-duplicate)' },
  overlapping: { label: 'Overlapping', color: 'var(--c-overlapping)' },
  factual:     { label: 'Factual',     color: 'var(--c-factual)' },
  diction:     { label: 'Diction',     color: 'var(--c-diction)' },
};

const els = {
  form:          document.getElementById('job-form'),
  audioDrop:     document.getElementById('audio-drop'),
  audioInput:    document.getElementById('audio-input'),
  audioFilename: document.getElementById('audio-filename'),
  originalText:  document.getElementById('original-text'),
  language:      document.getElementById('language'),
  submitBtn:     document.getElementById('submit-btn'),
  formError:     document.getElementById('form-error'),
  statusPanel:   document.getElementById('status-panel'),
  statusLabel:   document.getElementById('status-label'),
  resultsPanel:  document.getElementById('results-panel'),
  summary:       document.getElementById('summary'),
  timeline:      document.getElementById('timeline'),
  errorList:     document.getElementById('error-list'),
  legend:        document.getElementById('legend'),
};

function renderLegend() {
  els.legend.innerHTML = Object.values(ERROR_META)
    .map(
      (m) => `<span class="legend__item"><span class="legend__dot" style="background:${m.color}"></span>${m.label}</span>`
    )
    .join('');
}
renderLegend();

els.audioDrop.addEventListener('click', () => els.audioInput.click());
els.audioInput.addEventListener('change', () => {
  const file = els.audioInput.files[0];
  els.audioFilename.textContent = file ? file.name : 'wav · mp3 · m4a · ogg · flac';
});
['dragover', 'dragleave', 'drop'].forEach((evt) => {
  els.audioDrop.addEventListener(evt, (e) => {
    e.preventDefault();
    els.audioDrop.classList.toggle('is-active', evt === 'dragover');
    if (evt === 'drop' && e.dataTransfer.files[0]) {
      els.audioInput.files = e.dataTransfer.files;
      els.audioFilename.textContent = e.dataTransfer.files[0].name;
    }
  });
});

function fmtTime(seconds) {
  const s = Math.max(0, seconds || 0);
  const m = Math.floor(s / 60);
  const rem = (s % 60).toFixed(1);
  return `${m}:${rem.padStart(4, '0')}`;
}

function renderResults(result) {
  const errors = result.errors || [];
  const maxEnd = errors.reduce((max, e) => Math.max(max, e.end), 1);

  els.summary.innerHTML = `
    <div class="summary__stat"><strong>${errors.length}</strong><span>Errors found</span></div>
    <div class="summary__stat"><strong>${result.combined_silent_durations.toFixed(1)}s</strong><span>Silence in track</span></div>
  `;

  els.timeline.innerHTML = errors
    .map((e) => {
      const meta = ERROR_META[e.type] || { color: 'var(--ink-dim)' };
      const left = (e.start / maxEnd) * 100;
      const width = Math.max(((e.end - e.start) / maxEnd) * 100, 0.4);
      return `<div class="timeline__marker" title="${meta.label} · ${fmtTime(e.start)}" style="left:${left}%; width:${width}%; background:${meta.color}"></div>`;
    })
    .join('');

  if (errors.length === 0) {
    els.errorList.innerHTML = '<li class="empty-note">No errors found — the dub matches the script.</li>';
  } else {
    els.errorList.innerHTML = errors
      .map((e) => {
        const meta = ERROR_META[e.type] || { label: e.type, color: 'var(--ink-dim)' };
        const correction = e.correction
          ? `<span class="error-item__correction">${escapeHtml(e.correction)}</span>`
          : `<span class="error-item__correction"><em>no correction</em></span>`;
        return `
          <li class="error-item" style="border-left-color:${meta.color}">
            <span class="error-item__time">${fmtTime(e.start)}</span>
            <div class="error-item__body">
              <span class="error-item__type" style="color:${meta.color}">${meta.label}</span>
              ${correction}
            </div>
          </li>`;
      })
      .join('');
  }

  els.statusPanel.hidden = true;
  els.resultsPanel.hidden = false;
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

async function pollJob(jobId) {
  const labels = {
    queued: 'Queued…',
    processing: 'Transcribing and comparing against the script…',
  };
  const poll = async () => {
    const res = await fetch(`/api/v1/jobs/${jobId}`);
    if (!res.ok) {
      showFormError('Could not fetch job status.');
      resetForm();
      return;
    }
    const job = await res.json();
    if (job.status === 'done') {
      renderResults(job.result);
      return;
    }
    if (job.status === 'failed') {
      showFormError(`Processing failed: ${job.error || 'unknown error'}`);
      els.statusPanel.hidden = true;
      resetForm();
      return;
    }
    els.statusLabel.textContent = labels[job.status] || job.status;
    setTimeout(poll, 2000);
  };
  poll();
}

function showFormError(message) {
  els.formError.textContent = message;
}

function resetForm() {
  els.submitBtn.disabled = false;
  els.submitBtn.textContent = 'Run analysis';
}

els.form.addEventListener('submit', async (e) => {
  e.preventDefault();
  showFormError('');

  const audioFile = els.audioInput.files[0];
  const originalText = els.originalText.value.trim();

  if (!audioFile) {
    showFormError('Choose an audio file with the dub.');
    return;
  }
  if (!originalText) {
    showFormError('Paste the source text to compare against.');
    return;
  }

  const formData = new FormData();
  formData.append('audio', audioFile);
  formData.append('original_text', originalText);
  if (els.language.value.trim()) {
    formData.append('language', els.language.value.trim());
  }

  els.submitBtn.disabled = true;
  els.submitBtn.textContent = 'Uploading…';
  els.resultsPanel.hidden = true;

  try {
    const res = await fetch('/api/v1/jobs', { method: 'POST', body: formData });
    const data = await res.json();
    if (!res.ok) {
      showFormError(data.error || 'Could not start processing.');
      resetForm();
      return;
    }
    els.statusPanel.hidden = false;
    els.statusLabel.textContent = 'Queued…';
    pollJob(data.job_id);
  } catch (err) {
    showFormError('Network error. Please try again.');
    resetForm();
  }
});
