/* ============================================================
   Wavify — Frontend Logic
   ============================================================ */

const form       = document.getElementById('converter-form');
const urlInput   = document.getElementById('url-input');
const clearBtn   = document.getElementById('clear-btn');
const convertBtn = document.getElementById('convert-btn');
const statusArea = document.getElementById('status-area');
const previewPane= document.getElementById('preview-pane');

// ── Helpers ──────────────────────────────────────────────────

function fmtDuration(sec) {
  if (!sec) return '';
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  return h
    ? `${h}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`
    : `${m}:${String(s).padStart(2,'0')}`;
}

function setStatus(type, html, showProgress = false) {
  statusArea.innerHTML = `
    <div class="status-msg ${type}" role="status">
      ${type === 'loading' ? '<div class="spinner" aria-hidden="true"></div>' : ''}
      <span>${html}</span>
    </div>
    ${showProgress ? '<div class="progress-wrap"><div class="progress-bar" id="progress-bar"></div></div>' : ''}
  `;
}

function clearStatus() {
  statusArea.innerHTML = '';
}

function setConverting(active) {
  convertBtn.disabled = active;
  convertBtn.querySelector('.btn-text').textContent = active ? 'Converting…' : 'Convert';
}

function hidePreview() {
  previewPane.hidden = true;
  previewPane.innerHTML = `
    <div class="preview-inner">
      <img id="preview-thumb" class="preview-thumb" src="" alt="Video thumbnail" />
      <div class="preview-meta">
        <p id="preview-title" class="preview-title"></p>
        <p id="preview-channel" class="preview-channel"></p>
        <p id="preview-duration" class="preview-duration"></p>
      </div>
    </div>
  `;
}

// ── Clear button ─────────────────────────────────────────────

urlInput.addEventListener('input', () => {
  clearBtn.hidden = urlInput.value.length === 0;
  if (!urlInput.value) {
    hidePreview();
    clearStatus();
  }
});

clearBtn.addEventListener('click', () => {
  urlInput.value = '';
  clearBtn.hidden = true;
  urlInput.focus();
  hidePreview();
  clearStatus();
});

// ── Video preview fetch (debounced) ──────────────────────────

let previewTimer = null;

urlInput.addEventListener('input', () => {
  clearTimeout(previewTimer);
  const val = urlInput.value.trim();
  if (!val) return;

  previewTimer = setTimeout(() => fetchPreview(val), 900);
});

async function fetchPreview(url) {
  try {
    const res = await fetch(`/info?url=${encodeURIComponent(url)}`);
    if (!res.ok) return;
    const data = await res.json();
    if (data.error) return;

    // Rebuild elements (in case they were re-rendered)
    const thumb   = document.getElementById('preview-thumb') ?? previewPane.querySelector('.preview-thumb');
    const title   = document.getElementById('preview-title');
    const channel = document.getElementById('preview-channel');
    const dur     = document.getElementById('preview-duration');

    if (thumb)   { thumb.src = data.thumbnail; thumb.alt = data.title; }
    if (title)   title.textContent = data.title;
    if (channel) channel.textContent = data.channel;
    if (dur)     dur.textContent = fmtDuration(data.duration);

    previewPane.hidden = false;
  } catch (_) {
    // Silently ignore preview errors
  }
}

// ── Form submit ───────────────────────────────────────────────

form.addEventListener('submit', async (e) => {
  e.preventDefault();

  const url = urlInput.value.trim();
  if (!url) {
    setStatus('error', 'Please paste a YouTube URL first.');
    urlInput.focus();
    return;
  }

  setConverting(true);
  setStatus('loading', 'Fetching audio stream…', true);

  // Animate progress bar indeterminately
  let progress = 0;
  const progressInterval = setInterval(() => {
    const bar = document.getElementById('progress-bar');
    if (!bar) { clearInterval(progressInterval); return; }
    progress = Math.min(progress + Math.random() * 8, 88);
    bar.style.width = `${progress}%`;
  }, 400);

  try {
    const response = await fetch(`/convert?url=${encodeURIComponent(url)}`);

    clearInterval(progressInterval);

    if (!response.ok) {
      let msg = 'Conversion failed.';
      try {
        const err = await response.json();
        if (err.error) msg = err.error;
      } catch (_) {}
      setStatus('error', msg);
      setConverting(false);
      return;
    }

    // Fill progress to 100% with a brief delay
    const bar = document.getElementById('progress-bar');
    if (bar) bar.style.width = '100%';

    // Get filename from header
    const disposition = response.headers.get('Content-Disposition') || '';
    const match = disposition.match(/filename\*?=["']?(?:UTF-8'')?([^"';\n]+)/i);
    const filename = match ? decodeURIComponent(match[1]) : 'audio.wav';

    // Trigger browser download
    const blob = await response.blob();
    const blobUrl = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = blobUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(blobUrl), 10000);

    setStatus('success', `✓ <strong>${filename}</strong> downloaded successfully!`);

  } catch (err) {
    clearInterval(progressInterval);
    setStatus('error', 'Network error — is the server running?');
  } finally {
    setConverting(false);
  }
});

// ── Keyboard: Enter in input triggers form ────────────────────

urlInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') form.requestSubmit();
});
