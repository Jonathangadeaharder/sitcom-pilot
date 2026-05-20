<script lang="ts">
	import { invoke } from '@tauri-apps/api/core';
	import { listen } from '@tauri-apps/api/event';
	import { onMount, onDestroy } from 'svelte';

	let episodePath = $state('');
	let episodeMeta = $state<{
		show: string;
		season: number;
		episode: number;
		title: string;
		scenes: number;
		beats: number;
	} | null>(null);
	let status = $state<'idle' | 'validating' | 'valid' | 'invalid' | 'running' | 'done' | 'error'>('idle');
	let logs = $state<string[]>([]);
	let statusMessage = $state('');
	let outputVideoPath = $state('');
	let isDragging = $state(false);

	let logEnd: HTMLDivElement | undefined = $state();
	let fileInput: HTMLInputElement | undefined = $state();

	let unlistenLog: (() => void) | undefined;

	onMount(async () => {
		unlistenLog = await listen<string>('pipeline-log', (event) => {
			logs = [...logs, event.payload];
		});
	});

	onDestroy(() => {
		unlistenLog?.();
	});

	$effect(() => {
		if (logEnd) {
			logEnd.scrollIntoView({ behavior: 'smooth' });
		}
	});

	function handleDragOver(e: DragEvent) {
		e.preventDefault();
		isDragging = true;
	}

	function handleDragLeave() {
		isDragging = false;
	}

	function handleDrop(e: DragEvent) {
		e.preventDefault();
		isDragging = false;
		const files = e.dataTransfer?.files;
		if (files && files.length > 0) {
			loadFile(files[0].path);
		}
	}

	function handleFileSelect() {
		fileInput?.click();
	}

	function handleFileChange(e: Event) {
		const input = e.target as HTMLInputElement;
		if (input.files && input.files.length > 0) {
			loadFile(input.files[0].path);
		}
	}

	async function loadFile(path: string) {
		episodePath = path;
		status = 'validating';
		logs = [];
		outputVideoPath = '';
		episodeMeta = null;

		try {
			const result = await invoke<string>('validate_episode', { path });
			const data = JSON.parse(result);
			episodeMeta = {
				show: data.show,
				season: data.season,
				episode: data.episode,
				title: data.title,
				scenes: data.scenes?.length ?? 0,
				beats: data.scenes?.reduce((s: number, sc: { beats?: unknown[] }) => s + (sc.beats?.length ?? 0), 0) ?? 0
			};
			status = 'valid';
			statusMessage = 'Episode validated successfully';
		} catch (err) {
			status = 'invalid';
			statusMessage = `Validation failed: ${err}`;
		}
	}

	async function runPipeline() {
		if (!episodePath) return;
		status = 'running';
		logs = [];
		outputVideoPath = '';

		try {
			const result = await invoke<string>('run_pipeline', {
				path: episodePath,
				outputDir: '',
				workers: 2
			});
			const data = JSON.parse(result);
			status = 'done';
			statusMessage = 'Pipeline completed successfully';
			if (data.video_path) {
				outputVideoPath = data.video_path;
			}
		} catch (err) {
			status = 'error';
			statusMessage = `Pipeline failed: ${err}`;
		}
	}

	function reset() {
		episodePath = '';
		episodeMeta = null;
		status = 'idle';
		logs = [];
		statusMessage = '';
		outputVideoPath = '';
	}
</script>

<div class="page">
	{#if status === 'idle'}
		<div
			class="drop-zone"
			class:drop-zone--active={isDragging}
			ondragover={handleDragOver}
			ondragleave={handleDragLeave}
			ondrop={handleDrop}
			onclick={handleFileSelect}
			role="button"
			tabindex="0"
			onkeydown={(e) => e.key === 'Enter' && handleFileSelect()}
		>
			<input
				type="file"
				accept=".json"
				class="file-input"
				bind:this={fileInput}
				onchange={handleFileChange}
			/>
			<div class="drop-zone-icon">
				<svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
					<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
					<path d="M17 8l-5-5-5 5" />
					<path d="M12 3v12" />
				</svg>
			</div>
			<p class="drop-zone-text">Drop episode JSON here or click to browse</p>
			<p class="drop-zone-hint">Supports v2.0 episode schema files</p>
		</div>
	{:else}
		<div class="workspace">
			<div class="sidebar">
				<div class="episode-card">
					<div class="card-header">
						<h2>{episodeMeta?.title ?? 'Episode'}</h2>
						<span class="badge" class:badge--valid={status === 'valid' || status === 'done'} class:badge--running={status === 'running'} class:badge--error={status === 'error' || status === 'invalid'}>
							{status === 'validating' ? 'Validating...' : status === 'valid' ? 'Valid' : status === 'invalid' ? 'Invalid' : status === 'running' ? 'Running' : status === 'done' ? 'Done' : 'Error'}
						</span>
					</div>
					{#if episodeMeta}
						<div class="meta-grid">
							<div class="meta-item">
								<span class="meta-label">Show</span>
								<span class="meta-value">{episodeMeta.show}</span>
							</div>
							<div class="meta-item">
								<span class="meta-label">Season</span>
								<span class="meta-value">{episodeMeta.season}</span>
							</div>
							<div class="meta-item">
								<span class="meta-label">Episode</span>
								<span class="meta-value">{episodeMeta.episode}</span>
							</div>
							<div class="meta-item">
								<span class="meta-label">Scenes</span>
								<span class="meta-value">{episodeMeta.scenes}</span>
							</div>
							<div class="meta-item">
								<span class="meta-label">Beats</span>
								<span class="meta-value">{episodeMeta.beats}</span>
							</div>
						</div>
					{/if}
					<div class="card-actions">
						<button
							class="btn btn--primary"
							onclick={runPipeline}
							disabled={status !== 'valid' && status !== 'done' && status !== 'error'}
						>
							{#if status === 'running'}
								Running...
							{:else}
								Run Pipeline
							{/if}
						</button>
						<button class="btn btn--secondary" onclick={reset}>Reset</button>
					</div>
				</div>

				{#if statusMessage}
					<div class="status-msg" class:status-msg--error={status === 'error' || status === 'invalid'} class:status-msg--success={status === 'done' || status === 'valid'}>
						{statusMessage}
					</div>
				{/if}
			</div>

			<div class="main-panel">
				{#if logs.length > 0}
					<div class="log-panel">
						<div class="log-header">
							<h3>Pipeline Output</h3>
							<span class="log-count">{logs.length} lines</span>
						</div>
						<div class="log-content">
							{#each logs as log, i}
								<pre class="log-line" class:log-line--warn={log.includes('WARN') || log.includes('warning')} class:log-line--error={log.includes('ERROR') || log.includes('error')}>{log}</pre>
							{/each}
							<div bind:this={logEnd}></div>
						</div>
					</div>
				{:else if status === 'running'}
					<div class="log-panel log-panel--empty">
						<p class="log-empty-text">Waiting for pipeline output...</p>
					</div>
				{:else}
					<div class="log-panel log-panel--empty">
						<p class="log-empty-text">Drop an episode file to get started</p>
					</div>
				{/if}

				{#if outputVideoPath}
					<div class="video-preview">
						<h3>Rendered Episode</h3>
						<video controls class="preview-video">
							<source src={outputVideoPath} type="video/mp4" />
						</video>
					</div>
				{/if}
			</div>
		</div>
	{/if}
</div>

<style>
	.page {
		height: 100%;
		display: flex;
		flex-direction: column;
	}

	.drop-zone {
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 12px;
		border: 2px dashed var(--border);
		border-radius: var(--radius);
		background: var(--bg-secondary);
		cursor: pointer;
		transition: all 0.2s ease;
		min-height: 300px;
	}

	.drop-zone:hover,
	.drop-zone--active {
		border-color: var(--accent);
		background: var(--bg-tertiary);
	}

	.file-input {
		display: none;
	}

	.drop-zone-icon {
		color: var(--text-muted);
		transition: color 0.2s;
	}

	.drop-zone:hover .drop-zone-icon,
	.drop-zone--active .drop-zone-icon {
		color: var(--accent);
	}

	.drop-zone-text {
		font-size: 16px;
		font-weight: 500;
		color: var(--text-primary);
	}

	.drop-zone-hint {
		font-size: 13px;
		color: var(--text-secondary);
	}

	.workspace {
		display: grid;
		grid-template-columns: 320px 1fr;
		gap: 16px;
		height: 100%;
	}

	.sidebar {
		display: flex;
		flex-direction: column;
		gap: 12px;
	}

	.episode-card {
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		padding: 16px;
	}

	.card-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 12px;
	}

	.card-header h2 {
		font-size: 16px;
		font-weight: 600;
	}

	.badge {
		font-size: 11px;
		font-weight: 600;
		padding: 2px 8px;
		border-radius: 99px;
		background: var(--bg-tertiary);
		color: var(--text-secondary);
		text-transform: uppercase;
		letter-spacing: 0.04em;
	}

	.badge--valid {
		background: var(--success-bg);
		color: var(--success);
	}

	.badge--running {
		background: #1a2d3d;
		color: var(--accent);
	}

	.badge--error {
		background: var(--error-bg);
		color: var(--error);
	}

	.meta-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 8px;
		margin-bottom: 16px;
	}

	.meta-item {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.meta-label {
		font-size: 11px;
		color: var(--text-secondary);
		text-transform: uppercase;
		letter-spacing: 0.04em;
	}

	.meta-value {
		font-size: 14px;
		font-weight: 500;
		font-family: var(--font-mono);
	}

	.card-actions {
		display: flex;
		gap: 8px;
	}

	.btn {
		padding: 8px 16px;
		border-radius: var(--radius-sm);
		border: 1px solid transparent;
		font-size: 14px;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.15s ease;
		font-family: inherit;
	}

	.btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.btn--primary {
		background: var(--accent);
		color: #0d1117;
		flex: 1;
	}

	.btn--primary:hover:not(:disabled) {
		background: var(--accent-hover);
	}

	.btn--secondary {
		background: var(--bg-tertiary);
		color: var(--text-primary);
		border-color: var(--border);
	}

	.btn--secondary:hover:not(:disabled) {
		background: var(--bg-hover);
	}

	.status-msg {
		padding: 10px 14px;
		border-radius: var(--radius-sm);
		font-size: 13px;
		background: var(--bg-tertiary);
		border: 1px solid var(--border);
	}

	.status-msg--error {
		background: var(--error-bg);
		border-color: var(--error);
		color: var(--error);
	}

	.status-msg--success {
		background: var(--success-bg);
		border-color: var(--success);
		color: var(--success);
	}

	.main-panel {
		display: flex;
		flex-direction: column;
		gap: 16px;
		min-height: 0;
	}

	.log-panel {
		flex: 1;
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		display: flex;
		flex-direction: column;
		min-height: 0;
		overflow: hidden;
	}

	.log-panel--empty {
		align-items: center;
		justify-content: center;
	}

	.log-empty-text {
		color: var(--text-muted);
		font-size: 14px;
		font-style: italic;
	}

	.log-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 10px 14px;
		border-bottom: 1px solid var(--border);
		flex-shrink: 0;
	}

	.log-header h3 {
		font-size: 13px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.04em;
	}

	.log-count {
		font-size: 12px;
		color: var(--text-secondary);
		font-family: var(--font-mono);
	}

	.log-content {
		flex: 1;
		overflow-y: auto;
		padding: 8px 14px;
		font-family: var(--font-mono);
		font-size: 12px;
		line-height: 1.5;
		background: #010409;
	}

	.log-line {
		white-space: pre-wrap;
		word-break: break-all;
		color: var(--text-secondary);
	}

	.log-line--warn {
		color: var(--warning);
	}

	.log-line--error {
		color: var(--error);
	}

	.video-preview {
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		padding: 16px;
		flex-shrink: 0;
	}

	.video-preview h3 {
		font-size: 13px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		margin-bottom: 8px;
	}

	.preview-video {
		width: 100%;
		max-height: 360px;
		border-radius: var(--radius-sm);
		background: #000;
	}
</style>
