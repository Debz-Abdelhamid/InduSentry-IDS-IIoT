// ============================================================
// IDS-IIoT Dashboard - Two-Phase Version (CORRECTED)
// ============================================================

const socket = io();

console.log('Dashboard JS loaded');

// ============================================================
// DOM Elements
// ============================================================

const startBtn = document.getElementById('startBtn');
const exportBtn = document.getElementById('exportBtn');
const uploadBtn = document.getElementById('uploadBtn');

// Progress elements
const progressBar = document.getElementById('progressBar');
const samplesProcessedSpan = document.getElementById('samplesProcessed');
const totalSamplesTargetSpan = document.getElementById('totalSamplesTarget');
const elapsedTimeSpan = document.getElementById('elapsedTime');
const remainingTimeSpan = document.getElementById('remainingTime');

// Dataset info
const datasetNameSpan = document.getElementById('datasetName');
const datasetInfoSpan = document.getElementById('datasetInfo');

// Phase indicators
const phaseIndicator = document.getElementById('phaseIndicator');

// AutoEncoder elements
const aeErrorSpan = document.getElementById('aeError');
const aeThresholdSpan = document.getElementById('aeThreshold');
const aeDecisionBadge = document.getElementById('aeDecisionBadge');
const aeNormalCountSpan = document.getElementById('aeNormalCount');
const aeAnomalyCountSpan = document.getElementById('aeAnomalyCount');
const aeConfidenceCircle = document.getElementById('aeConfidenceCircle');
const aeConfidenceText = document.getElementById('aeConfidenceText');

// XGBoost elements
const xgbPredictionSpan = document.getElementById('xgbPrediction');
const oodScoreSpan = document.getElementById('oodScore');
const oodSampleIndexSpan = document.getElementById('oodSampleIndex');
const finalDecisionBadge = document.getElementById('finalDecisionBadge');
const xgbConfidenceCircle = document.getElementById('xgbConfidenceCircle');
const xgbConfidenceText = document.getElementById('xgbConfidenceText');
const xgbProgressContainer = document.getElementById('xgbProgressContainer');
const xgbProgressBar = document.getElementById('xgbProgressBar');
const xgbSamplesProcessedSpan = document.getElementById('xgbSamplesProcessed');
const xgbTotalSamplesTargetSpan = document.getElementById('xgbTotalSamplesTarget');
const xgbPhaseNoteSpan = document.getElementById('xgbPhaseNote');

// Global stats
const normalCountSpan = document.getElementById('normalCount');
const knownCountSpan = document.getElementById('knownCount');
const zeroDayCountSpan = document.getElementById('zeroDayCount');
const currentSampleSpan = document.getElementById('currentSample');

// Session info
const sessionInfoSpan = document.getElementById('sessionInfo');
const latencySpan = document.getElementById('latencyDisplay');
const attackDistributionDiv = document.getElementById('attackDistribution');

// ============================================================
// Variables
// ============================================================
let startTime = null;
let currentPhase = 1;
let phase1Total = 0;
let phase2Total = 0;
let phaseStartTime = null;

// ============================================================
// Button State Helpers
// ============================================================

function setProcessingState(isProcessing) {
    if (startBtn) {
        startBtn.disabled = isProcessing;
        if (isProcessing) {
            startBtn.classList.add('opacity-50', 'cursor-not-allowed');
            startBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
        } else {
            startBtn.classList.remove('opacity-50', 'cursor-not-allowed');
            startBtn.innerHTML = '<i class="fas fa-play"></i> Start Processing';
        }
    }
    if (uploadBtn) {
        uploadBtn.disabled = isProcessing;
        if (isProcessing) {
            uploadBtn.classList.add('opacity-50', 'cursor-not-allowed');
        } else {
            uploadBtn.classList.remove('opacity-50', 'cursor-not-allowed');
        }
    }
}

function setUploadingState(isUploading) {
    if (uploadBtn) {
        uploadBtn.disabled = isUploading;
        if (isUploading) {
            uploadBtn.classList.add('opacity-50', 'cursor-not-allowed');
            uploadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Uploading...';
        } else {
            uploadBtn.classList.remove('opacity-50', 'cursor-not-allowed');
            uploadBtn.innerHTML = '<i class="fas fa-upload"></i> Upload CSV';
        }
    }
}

// ============================================================
// Helper Functions
// ============================================================

function formatTime(seconds) {
    if (isNaN(seconds) || seconds < 0) return '00:00:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

function updateProgressBar(progress, current, total) {
    if (progressBar) progressBar.style.width = `${progress}%`;
    if (samplesProcessedSpan) {
        samplesProcessedSpan.textContent = `${current.toLocaleString()} / ${total.toLocaleString()} (${progress.toFixed(1)}%)`;
    }
    if (totalSamplesTargetSpan && total > 0) {
        totalSamplesTargetSpan.textContent = `Target: ${total.toLocaleString()}`;
    }
}

function updateXgbProgressBar(progress, current, total) {
    if (xgbProgressBar) xgbProgressBar.style.width = `${progress}%`;
    if (xgbSamplesProcessedSpan) {
        xgbSamplesProcessedSpan.textContent = `${current.toLocaleString()} / ${total.toLocaleString()} (${progress.toFixed(1)}%)`;
    }
    if (xgbTotalSamplesTargetSpan && total > 0) {
        xgbTotalSamplesTargetSpan.textContent = `Target: ${total.toLocaleString()}`;
    }
}

function updateCountSpan(span, value) {
    if (!span) return;
    const parsed = Number(value);
    if (!Number.isNaN(parsed)) {
        span.textContent = parsed.toLocaleString();
    }
}

function updateElapsedTime() {
    if (phaseStartTime && elapsedTimeSpan) {
        const elapsed = (Date.now() - phaseStartTime) / 1000;
        elapsedTimeSpan.textContent = formatTime(elapsed);
    }
}

function updateRemainingTime(elapsed, current, total) {
    if (remainingTimeSpan && current > 0) {
        const estimatedTotal = (elapsed / current) * total;
        const remaining = estimatedTotal - elapsed;
        remainingTimeSpan.textContent = formatTime(remaining > 0 ? remaining : 0);
    }
}

function updateAeConfidence(confidence) {
    if (!aeConfidenceCircle || !aeConfidenceText) return;
    const circumference = 125.6;
    const percent = Math.min(100, Math.max(0, confidence));
    const offset = circumference * (1 - percent / 100);
    aeConfidenceCircle.style.strokeDashoffset = offset;
    aeConfidenceText.textContent = `${Math.round(percent)}%`;
}

function updateXgbConfidence(confidence) {
    if (!xgbConfidenceCircle || !xgbConfidenceText) return;
    const circumference = 125.6;
    const percent = Math.min(100, Math.max(0, confidence));
    const offset = circumference * (1 - percent / 100);
    xgbConfidenceCircle.style.strokeDashoffset = offset;
    xgbConfidenceText.textContent = `${Math.round(percent)}%`;
}

function updateAttackDistribution(dist) {
    if (!attackDistributionDiv || !dist) return;
    
    const attackNames = Object.keys(dist).sort();
    if (attackNames.length === 0) {
        attackDistributionDiv.innerHTML = '<p class="text-white/40 text-center col-span-full">No attacks classified yet</p>';
        return;
    }
    
    const maxCount = Math.max(...Object.values(dist), 1);
    let html = '<div class="lg:col-span-3"><h4 class="text-[10px] font-black text-white/40 uppercase tracking-widest mb-4">Attack Distribution</h4>';
    
    for (const attack of attackNames) {
        const count = dist[attack];
        const percentage = (count / maxCount) * 100;
        html += `
            <div class="space-y-1 mb-3">
                <div class="flex justify-between text-[10px] font-bold text-white/60">
                    <span>${attack}</span>
                    <span>${count.toLocaleString()}</span>
                </div>
                <div class="h-1.5 bg-white/5 rounded-full overflow-hidden">
                    <div class="h-full bg-blue-500 rounded-full" style="width: ${percentage}%"></div>
                </div>
            </div>
        `;
    }
    html += '</div>';
    attackDistributionDiv.innerHTML = html;
}

function dismissToast(toast) {
    if (!toast) return;
    const timeoutId = toast.dataset.timeoutId;
    if (timeoutId) {
        clearTimeout(Number(timeoutId));
    }
    toast.classList.add('toast--hide');
    toast.addEventListener('animationend', () => toast.remove(), { once: true });
}

function showToast(message, type = 'info', duration = 4500) {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const iconMap = {
        success: 'fa-check-circle',
        error: 'fa-triangle-exclamation',
        warning: 'fa-exclamation-circle',
        info: 'fa-circle-info'
    };

    const toast = document.createElement('div');
    toast.className = `toast toast--${type}`;
    toast.setAttribute('role', 'status');

    const iconWrap = document.createElement('div');
    iconWrap.className = 'toast__icon';
    const icon = document.createElement('i');
    icon.className = `fas ${iconMap[type] || iconMap.info}`;
    iconWrap.appendChild(icon);

    const messageWrap = document.createElement('div');
    messageWrap.className = 'toast__message';
    messageWrap.textContent = message;

    const closeBtn = document.createElement('button');
    closeBtn.type = 'button';
    closeBtn.className = 'toast__close';
    closeBtn.setAttribute('aria-label', 'Dismiss');
    closeBtn.innerHTML = '&times;';
    closeBtn.addEventListener('click', () => dismissToast(toast));

    toast.appendChild(iconWrap);
    toast.appendChild(messageWrap);
    toast.appendChild(closeBtn);
    container.appendChild(toast);

    const timeoutId = window.setTimeout(() => dismissToast(toast), duration);
    toast.dataset.timeoutId = String(timeoutId);
}

// ============================================================
// Socket Events - PHASE 1 (AutoEncoder)
// ============================================================

socket.on('phase_2_ready', (data) => {
    if (phaseIndicator) {
        phaseIndicator.innerHTML = '<i class="fas fa-cog fa-spin mr-2"></i>Calibrating detection thresholds...';
        phaseIndicator.className = 'bg-yellow-600/20 text-yellow-400 px-4 py-2 rounded-lg text-xs font-bold';
    }
});

socket.on('phase_start', (data) => {
    console.log('phase_start received:', data);
    
    if (data.phase === 1) {
        currentPhase = 1;
        phase1Total = data.total;
        phaseStartTime = Date.now();
        if (phaseIndicator) {
            phaseIndicator.innerHTML = '<i class="fas fa-wave-square mr-2"></i>Phase 1: AutoEncoder Processing';
            phaseIndicator.className = 'bg-blue-600/20 text-blue-400 px-4 py-2 rounded-lg text-xs font-bold';
        }
        updateProgressBar(0, 0, phase1Total);
        if (xgbProgressContainer) xgbProgressContainer.classList.add('hidden');
        updateXgbProgressBar(0, 0, 0);
        if (xgbPhaseNoteSpan) xgbPhaseNoteSpan.textContent = 'Waiting for anomalies...';
    } else if (data.phase === 2) {
        currentPhase = 2;
        phase2Total = data.total;
        phaseStartTime = Date.now();
        if (phaseIndicator) {
            phaseIndicator.innerHTML = '<i class="fas fa-sitemap mr-2"></i>Phase 2: XGBoost + OOD Classification';
            phaseIndicator.className = 'bg-blue-600/20 text-blue-400 px-4 py-2 rounded-lg text-xs font-bold';
        }
        updateProgressBar(0, 0, phase2Total);
        if (xgbProgressContainer) xgbProgressContainer.classList.remove('hidden');
        updateXgbProgressBar(0, 0, phase2Total);
        if (xgbPhaseNoteSpan) xgbPhaseNoteSpan.textContent = 'Processing anomalies...';
        console.log('Phase 2 started, total anomalies:', phase2Total);
    }
});

socket.on('ae_sample_processed', (data) => {
    if (currentPhase !== 1) return;
    
    updateProgressBar(data.progress, data.sample_index, data.total);
    const elapsed = (Date.now() - phaseStartTime) / 1000;
    updateRemainingTime(elapsed, data.sample_index, data.total);
    
    if (aeErrorSpan) aeErrorSpan.textContent = data.ae_error.toFixed(4);
    if (aeThresholdSpan) aeThresholdSpan.textContent = data.ae_threshold.toFixed(3);
    updateAeConfidence(data.ae_confidence);
    
    if (aeDecisionBadge) {
        if (data.ae_decision === 'ANOMALY') {
            aeDecisionBadge.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Anomaly Detected';
            aeDecisionBadge.className = 'bg-red-500/20 text-red-400 px-4 py-1.5 rounded-full text-[10px] font-black tracking-widest uppercase border border-red-500/30 flex items-center gap-2';
        } else {
            aeDecisionBadge.innerHTML = '<i class="fas fa-check-circle"></i> Normal';
            aeDecisionBadge.className = 'bg-green-500/20 text-green-400 px-4 py-1.5 rounded-full text-[10px] font-black tracking-widest uppercase border border-green-500/30 flex items-center gap-2';
        }
    }
    
    if (currentSampleSpan) currentSampleSpan.textContent = `Current: #${data.sample_index}`;
    updateCountSpan(aeNormalCountSpan, data.normal_count);
    updateCountSpan(aeAnomalyCountSpan, data.anomaly_count);
    updateCountSpan(normalCountSpan, data.normal_count);
    updateElapsedTime();
});

socket.on('ae_phase_complete', (data) => {
    console.log('Phase 1 Complete:', data);
    
    // Update AE card with final stats
    updateCountSpan(aeNormalCountSpan, data.normal_count);
    updateCountSpan(aeAnomalyCountSpan, data.anomaly_count);
    
    const anomalyCount = Number(data.anomaly_count);
    if (phaseIndicator) {
        if (!Number.isNaN(anomalyCount) && anomalyCount === 0) {
            phaseIndicator.innerHTML = '<i class="fas fa-check-circle"></i> Phase 1 complete. No anomalies detected.';
        } else {
            phaseIndicator.innerHTML = '<i class="fas fa-check-circle"></i> Phase 1 complete. Starting Phase 2...';
        }
    }
    updateCountSpan(normalCountSpan, data.normal_count);
    if (xgbPhaseNoteSpan && !Number.isNaN(anomalyCount) && anomalyCount === 0) {
        xgbPhaseNoteSpan.textContent = 'No anomalies to process.';
    }
    
    console.log('Waiting for Phase 2 to start...');
});

// ============================================================
// Socket Events - PHASE 2 (XGBoost + OOD)
// ============================================================

socket.on('xgb_sample_processed', (data) => {
    console.log('XGB sample received:', data.sample_index, 'Phase:', currentPhase);
    
    if (currentPhase !== 2) {
        console.log('Not in Phase 2, ignoring XGB event');
        return;
    }
    
    updateProgressBar(data.progress, data.processed, data.total);
    updateXgbProgressBar(data.progress, data.processed, data.total);
    const elapsed = (Date.now() - phaseStartTime) / 1000;
    updateRemainingTime(elapsed, data.processed, data.total);
    
    if (xgbPredictionSpan) xgbPredictionSpan.textContent = data.xgb_prediction;
    updateXgbConfidence(data.xgb_confidence);
    
    if (oodScoreSpan) oodScoreSpan.textContent = data.ood_score.toFixed(4);
    if (oodSampleIndexSpan) oodSampleIndexSpan.textContent = `#${data.sample_index}`;
    
    if (finalDecisionBadge) {
        if (data.final_decision === 'ZERO-DAY') {
            finalDecisionBadge.innerHTML = '<i class="fas fa-skull-crossbones"></i> Zero-Day Attack';
            finalDecisionBadge.className = 'bg-orange-500/20 text-orange-400 px-4 py-1.5 rounded-full text-[10px] font-black tracking-widest uppercase border border-orange-500/30 flex items-center gap-2';
        } else {
            finalDecisionBadge.innerHTML = '<i class="fas fa-check-shield"></i> Known Attack';
            finalDecisionBadge.className = 'bg-blue-500/20 text-blue-400 px-4 py-1.5 rounded-full text-[10px] font-black tracking-widest uppercase border border-blue-500/30 flex items-center gap-2';
        }
    }
    
    if (currentSampleSpan) currentSampleSpan.textContent = `Anomaly #${data.sample_index}`;
    updateElapsedTime();
    
    // Update global stats in real-time
    updateCountSpan(knownCountSpan, data.known_count);
    updateCountSpan(zeroDayCountSpan, data.zero_day_count);
    if (data.attack_distribution) {
        updateAttackDistribution(data.attack_distribution);
    }
});

// ============================================================
// Socket Events - Final
// ============================================================

socket.on('processing_complete', (summary) => {
    setProcessingState(false);
    if (exportBtn) {
        exportBtn.disabled = false;
        exportBtn.classList.remove('opacity-50', 'cursor-not-allowed');
        exportBtn.title = '';
    }

    console.log('Processing Complete:', summary);
    
    if (phaseIndicator) phaseIndicator.innerHTML = '<i class="fas fa-flag-checkered"></i> Processing complete.';

    const xgbTotal = Number(summary.known_count || 0) + Number(summary.zero_day_count || 0);
    if (xgbTotal > 0) {
        updateProgressBar(100, xgbTotal, xgbTotal);
        updateXgbProgressBar(100, xgbTotal, xgbTotal);
        if (xgbPhaseNoteSpan) xgbPhaseNoteSpan.textContent = 'Completed.';
    }

    updateCountSpan(normalCountSpan, summary.normal_count);
    updateCountSpan(knownCountSpan, summary.known_count);
    updateCountSpan(zeroDayCountSpan, summary.zero_day_count);
    
    if (summary.attack_distribution) {
        updateAttackDistribution(summary.attack_distribution);
    }
    
    if (sessionInfoSpan && summary.timestamp) {
        const date = new Date(summary.timestamp);
        sessionInfoSpan.innerHTML = `<span>Session: ${date.toLocaleDateString()}</span><span>${date.toLocaleTimeString()}</span>`;
    }
    
    if (latencySpan && summary.latency_ms) {
        latencySpan.innerHTML = `<i class="fas fa-tachometer-alt text-blue-500/50"></i> LATENCY: ${summary.latency_ms}MS`;
    }
    
    currentPhase = 1;
    phaseStartTime = null;
});

socket.on('connect', () => console.log('Connected to backend'));
socket.on('connect_error', (error) => console.error('Connection error:', error));
socket.on('server_status', (data) => console.log('Server status:', data));
socket.on('processing_error', (data) => {
    setProcessingState(false);
    if (exportBtn) {
        exportBtn.disabled = false;
        exportBtn.classList.remove('opacity-50', 'cursor-not-allowed');
        exportBtn.title = '';
    }

    console.error('Error:', data.message);
    showToast(`Error: ${data.message}`, 'error');
    if (phaseIndicator) {
        phaseIndicator.innerHTML = '<i class="fas fa-triangle-exclamation mr-2"></i>Processing error.';
        phaseIndicator.className = 'bg-red-600/20 text-red-400 px-4 py-2 rounded-lg text-xs font-bold';
    }
    currentPhase = 1;
});
socket.on('processing_stopped', (data) => {
    setProcessingState(false);
    console.log('Stopped:', data.message);
    if (phaseIndicator) {
        phaseIndicator.innerHTML = '<i class="fas fa-stop-circle mr-2"></i>Processing stopped.';
        phaseIndicator.className = 'bg-yellow-600/20 text-yellow-400 px-4 py-2 rounded-lg text-xs font-bold';
    }
    showToast(data.message || 'Processing stopped.', 'warning');
    currentPhase = 1;
});

// ============================================================
// File Upload
// ============================================================

async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch('/upload', { method: 'POST', body: formData });
        const result = await response.json();
        
        if (response.ok) {
            console.log('Upload success:', result);
            if (datasetNameSpan) {
                datasetNameSpan.innerHTML = `${file.name} <i class="fas fa-check-circle ml-1"></i>`;
                datasetNameSpan.className = 'font-data-mono text-green-400 font-bold mt-1';
            }
            if (datasetInfoSpan && result.total_rows) {
                datasetInfoSpan.textContent = `${result.total_rows.toLocaleString()} total samples ready for analysis`;
            }
            showToast('File uploaded successfully.', 'success');
        } else {
            showToast(`Upload failed: ${result.error || 'Unknown error'}`, 'error');
        }
    } catch (error) {
        console.error('Upload error:', error);
        showToast(`Upload error: ${error.message}`, 'error');
    }
}

// ============================================================
// Button Handlers
// ============================================================

// Disable export by default; enable only when server says processing_complete.
if (exportBtn) {
    exportBtn.disabled = true;
    exportBtn.classList.add('opacity-50', 'cursor-not-allowed');
    exportBtn.title = 'Export is available after processing completes.';
}

if (startBtn) {
    startBtn.addEventListener('click', () => {
        console.log('Start button clicked');
        const datasetPath = sessionStorage.getItem('datasetPath');
        if (!datasetPath) {
            showToast('Please upload a CSV file first.', 'warning');
            return;
        }
        currentPhase = 1;
        setProcessingState(true);
        if (exportBtn) {
            exportBtn.disabled = true;
            exportBtn.classList.add('opacity-50', 'cursor-not-allowed');
            exportBtn.title = 'Export is available after processing completes.';
        }
        showToast('Processing dataset — Phase 1 starting...', 'info', 6000);
        socket.emit('start_processing', { path: datasetPath });
    });
}

// Store dataset path after upload
const originalUploadFile = uploadFile;
window.uploadFile = async function(file) {

    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch('/upload', { method: 'POST', body: formData });
    const result = await response.json();
    if (response.ok) {
        sessionStorage.setItem('datasetPath', result.path);
        if (datasetNameSpan) {
            datasetNameSpan.innerHTML = `${file.name} <i class="fas fa-check-circle ml-1"></i>`;
            datasetNameSpan.className = 'font-data-mono text-green-400 font-bold mt-1';
        }
        if (datasetInfoSpan && result.total_rows) {
            datasetInfoSpan.textContent = `${result.total_rows.toLocaleString()} total samples ready for analysis`;
        }
        showToast('File uploaded successfully.', 'success');
        if (startBtn) startBtn.classList.remove('hidden');
    } else {
        showToast(`Upload failed: ${result.error || 'Unknown error'}`, 'error');
    }
};

if (exportBtn) {
    exportBtn.addEventListener('click', async () => {
        console.log('Export button clicked');

        // If processing is running, block UI click (server will also protect)
        if (exportBtn.disabled) return;

        try {
            const resp = await fetch('/export', { method: 'GET' });

            if (!resp.ok) {
                // Expect JSON error
                let msg = `Export failed (${resp.status})`;
                try {
                    const data = await resp.json();
                    if (data && data.error) msg = data.error;
                    else if (data && data.message) msg = data.message;
                } catch (e) {
                    // ignore parse errors
                }
                showToast(msg, 'error');
                return;
            }

            const blob = await resp.blob();
            const url = window.URL.createObjectURL(blob);

            const a = document.createElement('a');
            a.href = url;
            a.download = 'ids_report.pdf';
            document.body.appendChild(a);
            a.click();
            a.remove();

            window.URL.revokeObjectURL(url);
        } catch (err) {
            console.error(err);
            showToast(`Export error: ${err.message || err}`, 'error');
        }
    });
}



if (uploadBtn) {
    uploadBtn.addEventListener('click', () => {
        const fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.accept = '.csv';
        fileInput.onchange = async (e) => {
            const file = e.target.files[0];
            if (!file) return;
            setUploadingState(true);
            try {
                await window.uploadFile(file);
            } finally {
                setUploadingState(false);
            }
        };
        fileInput.click();
    });
}

setInterval(() => updateElapsedTime(), 1000);

// Live date in header
const sessionDateEl = document.getElementById('sessionDateDisplay');
if (sessionDateEl) {
    const now = new Date();
    sessionDateEl.textContent = now.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }).toUpperCase();
}

console.log('Dashboard JS ready - Two-Phase Version (Corrected)');

