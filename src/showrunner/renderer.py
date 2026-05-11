from __future__ import annotations

import copy
import logging
import time
from dataclasses import dataclass
from typing import Any

from showrunner.comfyui_client import ComfyUIClient
from showrunner.loader import EpisodeData, SceneData, ShotData
from showrunner.node_map import NodeMap
from showrunner.prompts import PromptBuilder

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RenderResult:
    shot_id: str
    prompt_id: str
    success: bool


class ShotRenderer:
    def __init__(
        self,
        client: ComfyUIClient,
        builder: PromptBuilder,
        node_map: NodeMap | None = None,
        cooldown_seconds: float = 0.0,
        crash_recovery: bool = False,
        server_cmd: list[str] | None = None,
        server_cwd: str | None = None,
        max_crash_retries: int = 3,
    ):
        self._client = client
        self._builder = builder
        self._node_map = node_map or NodeMap()
        self._cooldown_seconds = cooldown_seconds
        self._crash_recovery = crash_recovery
        self._server_cmd = server_cmd
        self._server_cwd = server_cwd
        self._max_crash_retries = max_crash_retries

    def _inject_workflow(
        self,
        shot: ShotData,
        scene: SceneData,
        episode: EpisodeData,
        workflow_template: dict[str, Any],
    ) -> dict[str, Any]:
        workflow = copy.deepcopy(workflow_template)
        nm = self._node_map

        env_data = episode.environments.get(scene.environment)
        if env_data and nm.env_profile in workflow:
            workflow[nm.env_profile].setdefault("inputs", {})["lora_name"] = (
                f"{env_data.profile}.safetensors"
            )

        for idx, char_name in enumerate(scene.characters_present):
            if idx >= len(nm.char_profiles):
                break
            char_data = episode.cast.get(char_name)
            if char_data:
                node_id = nm.char_profiles[idx]
                if node_id in workflow:
                    workflow[node_id].setdefault("inputs", {})["lora_name"] = (
                        f"{char_data.profile}.safetensors"
                    )

        start_prompt = self._builder.build_start_prompt(shot, scene, episode)
        end_prompt = self._builder.build_end_prompt(shot, scene, episode)

        if nm.start_prompt in workflow:
            workflow[nm.start_prompt].setdefault("inputs", {})["text"] = start_prompt
        else:
            logger.warning("Workflow missing node '%s'; start prompt not injected", nm.start_prompt)
        if nm.end_prompt in workflow:
            workflow[nm.end_prompt].setdefault("inputs", {})["text"] = end_prompt
        else:
            logger.warning("Workflow missing node '%s'; end prompt not injected", nm.end_prompt)
        if nm.seed in workflow:
            workflow[nm.seed].setdefault("inputs", {})["seed"] = shot.seed
        else:
            logger.warning("Workflow missing node '%s'; seed not injected", nm.seed)
        if nm.audio in workflow:
            workflow[nm.audio].setdefault("inputs", {})["audio"] = shot.audio_path
        else:
            logger.warning("Workflow missing node '%s'; audio path not injected", nm.audio)
        return workflow

    def render_shot(
        self,
        shot: ShotData,
        scene: SceneData,
        episode: EpisodeData,
        workflow_template: dict[str, Any],
    ) -> RenderResult:
        workflow = self._inject_workflow(shot, scene, episode, workflow_template)

        if not self._crash_recovery:
            prompt_id = self._client.queue_prompt(workflow)
            success = self._client.wait_for_completion(prompt_id)
            return RenderResult(shot_id=shot.shot_id, prompt_id=prompt_id, success=success)

        last_error = None
        for attempt in range(self._max_crash_retries):
            try:
                prompt_id = self._client.queue_prompt(workflow)
                success = self._client.wait_for_completion(prompt_id)
                return RenderResult(shot_id=shot.shot_id, prompt_id=prompt_id, success=success)
            except Exception as exc:
                last_error = exc
                logger.warning(f"Render attempt {attempt + 1} failed for {shot.shot_id}: {exc}")
                if not self._client.is_server_running():
                    logger.info("Server appears down, restarting...")
                    self._client.ensure_server_running(self._server_cmd, self._server_cwd)
        assert last_error is not None
        raise last_error

    def render_scene(
        self,
        scene: SceneData,
        episode: EpisodeData,
        workflow_template: dict[str, Any],
    ) -> list[RenderResult]:
        results = []
        for shot in scene.shots:
            logger.info(f"Rendering {shot.shot_id}")
            results.append(self.render_shot(shot, scene, episode, workflow_template))
            if self._cooldown_seconds > 0:
                logger.info(f"Cooldown {self._cooldown_seconds}s")
                time.sleep(self._cooldown_seconds)
        return results

    def render_episode(
        self,
        episode: EpisodeData,
        workflow_template: dict[str, Any],
    ) -> dict[str, list[RenderResult]]:
        results = {}
        for scene in episode.scenes:
            results[scene.scene_id] = self.render_scene(scene, episode, workflow_template)
        return results
