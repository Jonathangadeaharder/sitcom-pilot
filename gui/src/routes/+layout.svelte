<script lang="ts">
	import '../app.css';
	let { children } = $props();
</script>

<div class="app-shell">
	<header class="app-header">
		<h1 class="app-title">Showrunner</h1>
		<span class="app-subtitle">AI Episode Pipeline</span>
	</header>
	<main class="app-main">
		{@render children()}
	</main>
</div>

<style>
	:global(*) {
		margin: 0;
		padding: 0;
		box-sizing: border-box;
	}

	:global(body) {
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
		background: #0d1117;
		color: #e6edf3;
		overflow: hidden;
		height: 100vh;
		width: 100vw;
	}

	.app-shell {
		display: flex;
		flex-direction: column;
		height: 100vh;
	}

	.app-header {
		display: flex;
		align-items: baseline;
		gap: 12px;
		padding: 16px 24px;
		background: #161b22;
		border-bottom: 1px solid #30363d;
		flex-shrink: 0;
	}

	.app-title {
		font-size: 20px;
		font-weight: 700;
		color: #f0f6fc;
		letter-spacing: -0.02em;
	}

	.app-subtitle {
		font-size: 13px;
		color: #8b949e;
		font-weight: 400;
	}

	.app-main {
		flex: 1;
		overflow: auto;
		padding: 24px;
	}
</style>
