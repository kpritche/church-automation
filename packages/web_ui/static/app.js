// Church Automation Web UI - Client-side JavaScript

// State management
const jobPollers = {};

// API Base URL
const API_BASE = '';

/**
 * Trigger a job (announcements, slides, or bulletins)
 */
async function triggerJob(jobType) {
    const card = document.getElementById(`${jobType}-card`);
    const button = card.querySelector('.btn-primary');
    const progress = document.getElementById(`${jobType}-progress`);
    const errorDiv = document.getElementById(`${jobType}-error`);
    const successDiv = document.getElementById(`${jobType}-success`);
    const statusBadge = document.getElementById(`${jobType}-status`);

    // Reset UI
    button.disabled = true;
    progress.style.display = 'flex';
    errorDiv.style.display = 'none';
    successDiv.style.display = 'none';
    statusBadge.textContent = 'Queued';
    statusBadge.className = 'status-badge running';

    try {
        const response = await fetch(`${API_BASE}/api/jobs`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ job_type: jobType })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to start job');
        }

        const data = await response.json();
        console.log(`Job started: ${data.job_id}`);

        // Start polling for status
        pollJobStatus(data.job_id, jobType);

    } catch (error) {
        console.error('Error triggering job:', error);
        button.disabled = false;
        progress.style.display = 'none';
        errorDiv.textContent = `Error: ${error.message}`;
        errorDiv.style.display = 'block';
        statusBadge.textContent = 'Failed';
        statusBadge.className = 'status-badge failed';
    }
}

/**
 * Poll job status with exponential backoff
 */
function pollJobStatus(jobId, jobType) {
    const statusBadge = document.getElementById(`${jobType}-status`);
    const progress = document.getElementById(`${jobType}-progress`);
    const errorDiv = document.getElementById(`${jobType}-error`);
    const successDiv = document.getElementById(`${jobType}-success`);
    const button = document.querySelector(`#${jobType}-card .btn-primary`);

    let pollCount = 0;
    const maxPolls = 180; // 6 minutes max (assuming 2s intervals)

    const pollInterval = setInterval(async () => {
        pollCount++;

        try {
            const response = await fetch(`${API_BASE}/api/jobs/${jobId}`);
            
            if (!response.ok) {
                throw new Error('Failed to fetch job status');
            }

            const job = await response.json();
            console.log(`Job ${jobId} status:`, job.status);

            // Update status badge
            statusBadge.textContent = capitalizeFirst(job.status);
            statusBadge.className = `status-badge ${job.status}`;

            if (job.status === 'completed') {
                clearInterval(pollInterval);
                delete jobPollers[jobId];
                
                progress.style.display = 'none';
                successDiv.style.display = 'block';
                button.disabled = false;

                // For slides, show uploaded files list instead of download links
                if (jobType === 'slides') {
                    const uploadedFilesDiv = document.getElementById('slides-uploaded-files');
                    if (uploadedFilesDiv) {
                        if (job.uploaded_files && job.uploaded_files.length > 0) {
                            uploadedFilesDiv.innerHTML = '<strong>Uploaded to Planning Center:</strong><ul style="margin: 4px 0 0 16px;">' +
                                job.uploaded_files.map(f => `<li>${escapeHtml(f)}</li>`).join('') + '</ul>';
                        } else {
                            uploadedFilesDiv.innerHTML = '<em>No new files uploaded (all items already up to date).</em>';
                        }
                    }
                }

                // Refresh recent jobs list
                refreshJobs();
                
            } else if (job.status === 'failed') {
                clearInterval(pollInterval);
                delete jobPollers[jobId];
                
                progress.style.display = 'none';
                errorDiv.textContent = `Job failed: ${job.error || 'Unknown error'}`;
                errorDiv.style.display = 'block';
                button.disabled = false;
                
                // Refresh recent jobs list
                refreshJobs();
                
            } else if (pollCount >= maxPolls) {
                // Timeout - stop polling but don't mark as failed
                clearInterval(pollInterval);
                delete jobPollers[jobId];
                
                progress.style.display = 'none';
                errorDiv.textContent = 'Job is taking longer than expected. Check recent jobs below.';
                errorDiv.style.display = 'block';
                button.disabled = false;
            }

        } catch (error) {
            console.error('Error polling job status:', error);
            // Continue polling - might be temporary network issue
        }

    }, 2000); // Poll every 2 seconds

    jobPollers[jobId] = pollInterval;
}

/**
 * Show files for a specific job type
 */
async function showFiles(jobType) {
    const filesSection = document.getElementById('files-section');
    const filesList = document.getElementById('files-list');

    filesSection.style.display = 'block';
    filesList.innerHTML = '<p class="text-center">Loading files...</p>';

    try {
        const response = await fetch(`${API_BASE}/api/files/${jobType}`);
        
        if (!response.ok) {
            throw new Error('Failed to fetch files');
        }

        const data = await response.json();
        
        if (data.files.length === 0) {
            filesList.innerHTML = '<p class="no-jobs">No files found for this job type.</p>';
            return;
        }

        if (jobType === 'leader_guide') {
            renderLeaderGuideFiles(data.files);
            return;
        }

        // Render files (generic flat list)
        filesList.innerHTML = data.files.map(file => `
            <div class="file-item">
                <div class="file-info">
                    <div class="file-name">${escapeHtml(file.filename)}</div>
                    <div class="file-meta">
                        Date: ${file.date} | 
                        Size: ${formatBytes(file.size)} | 
                        Modified: ${formatDateTime(file.modified)}
                    </div>
                </div>
                <div class="file-actions">
                    <a href="${API_BASE}/api/files/${jobType}/${file.date}/${encodeURIComponent(file.filename)}" 
                       class="btn btn-primary btn-small"
                       download="${file.filename}">
                        Download
                    </a>
                </div>
            </div>
        `).join('');

    } catch (error) {
        console.error('Error loading files:', error);
        filesList.innerHTML = `<p class="error-message">Error loading files: ${error.message}</p>`;
    }
}

/**
 * Render leader guide files grouped by service in columns.
 */
function renderLeaderGuideFiles(files) {
    const filesList = document.getElementById('files-list');

    // Group by service slug, preserving discovery order (already sorted newest-first by mtime)
    const serviceOrder = [];
    const byService = {};
    for (const file of files) {
        const key = file.service || 'unknown';
        if (!byService[key]) {
            byService[key] = { service_name: file.service_name || key, variants: {} };
            serviceOrder.push(key);
        }
        // Keep only the most-recent file for each variant within this service
        const variant = file.variant || 'unknown';
        if (!byService[key].variants[variant]) {
            byService[key].variants[variant] = file;
        }
    }

    if (serviceOrder.length === 0) {
        filesList.innerHTML = '<p class="no-jobs">No leader guide files found.</p>';
        return;
    }

    const VARIANT_ORDER = ['sheet_music', 'chord_charts'];
    const VARIANT_ICONS = { sheet_music: '🎼', chord_charts: '🎸' };

    const columnsHtml = serviceOrder.map(serviceKey => {
        const svc = byService[serviceKey];

        // Determine a shared date label from any variant
        const anyFile = Object.values(svc.variants)[0];
        const dateLabel = anyFile ? anyFile.date : '';

        // Render each variant as a row inside the column
        const allVariants = VARIANT_ORDER.filter(v => svc.variants[v])
            .concat(Object.keys(svc.variants).filter(v => !VARIANT_ORDER.includes(v)));

        const variantRows = allVariants.map(variantKey => {
            const file = svc.variants[variantKey];
            const icon = VARIANT_ICONS[variantKey] || '📄';
            const label = file.variant_label || variantKey.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
            return `
                <div class="leader-guide-variant">
                    <div class="leader-guide-variant-info">
                        <span class="leader-guide-variant-icon">${icon}</span>
                        <div>
                            <div class="leader-guide-variant-label">${escapeHtml(label)}</div>
                            <div class="leader-guide-variant-meta">${formatBytes(file.size)}</div>
                        </div>
                    </div>
                    <a href="${API_BASE}/api/files/leader_guide/${encodeURIComponent(file.date)}/${encodeURIComponent(file.filename)}"
                       class="btn btn-primary btn-small"
                       download="${escapeHtml(file.filename)}">
                        Download
                    </a>
                </div>
            `;
        }).join('');

        return `
            <div class="leader-guide-column">
                <div class="leader-guide-column-header">
                    <span class="leader-guide-service-name">${escapeHtml(svc.service_name)}</span>
                    ${dateLabel ? `<span class="leader-guide-date">${escapeHtml(dateLabel)}</span>` : ''}
                </div>
                ${variantRows}
            </div>
        `;
    }).join('');

    filesList.innerHTML = `<div class="leader-guide-columns">${columnsHtml}</div>`;
}

/**
 * Hide files section
 */
function hideFiles() {
    document.getElementById('files-section').style.display = 'none';
}

/**
 * Refresh recent jobs list
 */
async function refreshJobs() {
    const jobsList = document.getElementById('jobs-list');
    
    try {
        const response = await fetch(`${API_BASE}/api/jobs`);
        
        if (!response.ok) {
            throw new Error('Failed to fetch jobs');
        }

        const data = await response.json();
        
        if (data.jobs.length === 0) {
            jobsList.innerHTML = '<p class="no-jobs">No recent jobs</p>';
            return;
        }

        // Sort by started_at descending
        const sortedJobs = data.jobs.sort((a, b) => 
            new Date(b.started_at) - new Date(a.started_at)
        );

        // Render jobs
        jobsList.innerHTML = sortedJobs.map(job => {
            const statusClass = job.status === 'completed' ? 'success-color' :
                               job.status === 'failed' ? 'error-color' :
                               'warning-color';
            
            return `
                <div class="job-item">
                    <div class="job-info">
                        <div class="job-type">${capitalizeFirst(job.type)}</div>
                        <div class="job-meta">
                            Status: <span style="color: var(--${statusClass}); font-weight: 600;">${capitalizeFirst(job.status)}</span> | 
                            Started: ${formatDateTime(job.started_at)}
                            ${job.completed_at ? ` | Completed: ${formatDateTime(job.completed_at)}` : ''}
                            ${job.error ? `<br><span style="color: var(--error-color);">Error: ${escapeHtml(job.error)}</span>` : ''}
                        </div>
                    </div>
                </div>
            `;
        }).join('');

    } catch (error) {
        console.error('Error loading jobs:', error);
        jobsList.innerHTML = `<p class="error-message">Error loading jobs: ${error.message}</p>`;
    }
}

// Utility functions

function capitalizeFirst(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function formatDateTime(isoString) {
    const date = new Date(isoString);
    return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log('Church Automation Web UI loaded');
    refreshJobs();
    
    // Refresh jobs every 30 seconds
    setInterval(refreshJobs, 30000);
});
