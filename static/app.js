'use strict';

// ── State ──────────────────────────────────────────────────────────────────
let activeTab = 'url';
let selectedFile = null;
let downloadUrl = null;

// ── DOM refs ───────────────────────────────────────────────────────────────
const tabs        = document.querySelectorAll('.tab');
const panelUrl    = document.getElementById('panel-url');
const panelFile   = document.getElementById('panel-file');
const urlInput    = document.getElementById('url-input');
const dropZone    = document.getElementById('drop-zone');
const fileInput   = document.getElementById('file-input');
const fileNameEl  = document.getElementById('file-name');
const browseTrig  = document.getElementById('browse-trigger');
const modelSelect = document.getElementById('model-select');
const submitBtn   = document.getElementById('submit-btn');
const loadingEl   = document.getElementById('loading');
const loadingMsg  = document.getElementById('loading-msg');
const errorBox    = document.getElementById('error-box');
const errorMsg    = document.getElementById('error-msg');
const resultBox   = document.getElementById('result-box');
const resultText  = document.getElementById('result-text');
const downloadBtn = document.getElementById('download-btn');
const copyBtn     = document.getElementById('copy-btn');

// ── Tab switching ──────────────────────────────────────────────────────────
tabs.forEach(tab => {
  tab.addEventListener('click', () => {
    activeTab = tab.dataset.tab;
    tabs.forEach(t => {
      t.classList.toggle('active', t === tab);
      t.setAttribute('aria-selected', t === tab);
    });
    panelUrl.classList.toggle('active', activeTab === 'url');
    panelFile.classList.toggle('active', activeTab === 'file');
    hideStatus();
  });
});

// ── File input ─────────────────────────────────────────────────────────────
browseTrig.addEventListener('click', () => fileInput.click());
dropZone.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', () => {
  if (fileInput.files[0]) setFile(fileInput.files[0]);
});

dropZone.addEventListener('dragover', e => {
  e.preventDefault();
  dropZone.classList.add('over');
});
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('over'));
dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('over');
  const f = e.dataTransfer.files[0];
  if (f) setFile(f);
});

function setFile(f) {
  selectedFile = f;
  fileNameEl.textContent = `Selected: ${f.name}`;
}

// ── Submit ─────────────────────────────────────────────────────────────────
submitBtn.addEventListener('click', handleSubmit);

async function handleSubmit() {
  hideStatus();
  hideResult();

  const model = modelSelect.value;

  if (activeTab === 'url') {
    const url = urlInput.value.trim();
    if (!url) return showError('Please enter a video URL.');
    await runTranscribe({ url, model });
  } else {
    if (!selectedFile) return showError('Please select a video file.');
    await runTranscribe({ file: selectedFile, model });
  }
}

async function runTranscribe({ url, file, model }) {
  setLoading(true, 'Processing… this may take a few minutes.');
  submitBtn.disabled = true;

  const form = new FormData();
  if (url)  form.append('url', url);
  if (file) form.append('file', file, file.name);
  form.append('model', model);

  try {
    const res = await fetch('/transcribe', { method: 'POST', body: form });
    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || `Server error ${res.status}`);
    }

    downloadUrl = data.download_url;
    showResult(data.text);
  } catch (err) {
    showError(err.message || 'Something went wrong.');
  } finally {
    setLoading(false);
    submitBtn.disabled = false;
  }
}

// ── Download ───────────────────────────────────────────────────────────────
downloadBtn.addEventListener('click', () => {
  if (!downloadUrl) return;
  const a = document.createElement('a');
  a.href = downloadUrl;
  a.download = 'transcript.txt';
  a.click();
});

// ── Copy ───────────────────────────────────────────────────────────────────
copyBtn.addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(resultText.value);
    copyBtn.textContent = '✓ Copied';
    copyBtn.classList.add('copied');
    setTimeout(() => {
      copyBtn.textContent = '⚗ Copy';
      copyBtn.classList.remove('copied');
    }, 2000);
  } catch {
    copyBtn.textContent = 'Failed';
  }
});

// ── Helpers ────────────────────────────────────────────────────────────────
function setLoading(on, msg = '') {
  loadingEl.classList.toggle('hidden', !on);
  if (msg) loadingMsg.textContent = msg;
}

function showError(msg) {
  errorMsg.textContent = msg;
  errorBox.classList.remove('hidden');
}

function hideStatus() {
  loadingEl.classList.add('hidden');
  errorBox.classList.add('hidden');
}

function showResult(text) {
  resultText.value = text;
  resultBox.classList.remove('hidden');
  resultBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function hideResult() {
  resultBox.classList.add('hidden');
  resultText.value = '';
  downloadUrl = null;
}
