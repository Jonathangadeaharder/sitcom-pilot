from __future__ import annotations

import copy
import logging
import time
from dataclasses import dataclass
from typing import Any

from showrunner.comfyui_client import ComfyUIClient
from showrunner.node_map import NodeMap
from showrunner.prompts import PromptBuilder
from showrunner.schemas.episode import EpisodeData, Scene, Shot

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

    def _inject_node_input(
        self, workflow: dict[str, Any], node_id: str | None, key: str, value: Any, label: str
    ) -> None:
        if node_id is None:
            return
        if node_id in workflow:
            workflow[node_id].setdefault("inputs", {})[key] = value
        else:
            logger.warning("Workflow missing node '%s'; %s not injected", node_id, label)

    def _inject_environment_lora(
        self, workflow: dict[str, Any], scene: Scene, episode: EpisodeData
    ) -> None:
        env_data = episode.environments.get(scene.environment)
        if env_data:
            self._inject_node_input(
                workflow,
                self._node_map.env_profile,
                "lora_name",
                f"{env_data.profile}.safetensors",
                "env lora",
            )

    def _inject_character_loras(
        self, workflow: dict[str, Any], scene: Scene, episode: EpisodeData
    ) -> None:
        nm = self._node_map
        for idx, char_name in enumerate(scene.characters_present):
            if idx >= len(nm.char_profiles):
                break
            char_data = episode.cast.get(char_name)
            if char_data:
                self._inject_node_input(
                    workflow,
                    nm.char_profiles[idx],
                    "lora_name",
                    f"{char_data.profile}.safetensors",
                    f"char lora {char_name}",
                )

    def _inject_workflow(
        self,
        shot: Shot,
        scene: Scene,
        episode: EpisodeData,
        workflow_template: dict[str, Any],
    ) -> dict[str, Any]:
        workflow = copy.deepcopy(workflow_template)
        nm = self._node_map

        self._inject_environment_lora(workflow, scene, episode)
        self._inject_character_loras(workflow, scene, episode)

        start_prompt = self._builder.build_start_prompt(shot, scene, episode)
        end_prompt = self._builder.build_end_prompt(shot, scene, episode)

        for node_id, key, value, label in [
            (nm.start_prompt, "text", start_prompt, "start prompt"),
            (nm.end_prompt, "text", end_prompt, "end prompt"),
            (nm.seed, "seed", shot.seed, "seed"),
            (nm.audio, "audio", shot.audio_path, "audio path"),
        ]:
            self._inject_node_input(workflow, node_id, key, value, label)

        return workflow

    def render_shot(
        self,
        shot: Shot,
        scene: Scene,
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
        scene: Scene,
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
