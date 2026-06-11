# TDD-010: `ComfyUIClient` hand-rolls retry, polling, and server lifecycle over `urllib`

- Status: Open
- Date: 2026-06-11
- Category: Reinvented wheel / Bad practice
- Severity: Medium

## Finding

`src/showrunner/comfyui_client.py`: manual exponential backoff (`time.sleep(2**attempt)`, ~lines 39–57) over raw `urllib.request`; a `while time.time() - start < timeout` polling loop (~lines 59–75); server startup via `subprocess.Popen` + fixed `time.sleep(10)`; and silent error swallowing (`except Exception: pass` ~line 72, `except Exception: return []` ~line 81). Neither `httpx` nor `requests` is a dependency, though the aiservices stack already uses `requests`.

## Why it matters

This is v1 ComfyUI plumbing that belongs in the platform (scriptforge/AIServices own backend integrations), and the silent excepts make render failures undiagnosable.

## Recommendation

Treat `ComfyUIClient` + `ShotRenderer` + `node_map.py` as a v1 deletion candidate once the v2 beat pipeline is the sole path; any surviving HTTP code moves to `httpx`/`requests` with logged failures.
