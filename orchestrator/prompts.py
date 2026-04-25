from __future__ import annotations


class PromptBuilder:
    QUALITY_SUFFIX = " -- RAW photo, 8k resolution"

    def _character_triggers(self, scene, episode) -> str:
        parts = []
        for name in scene.characters_present:
            char = episode.cast.get(name)
            if char:
                parts.append(char.trigger_word)
        return ", ".join(parts)

    def build_start_prompt(self, shot, scene, episode) -> str:
        env = episode.environments.get(scene.environment)
        env_trigger = env.trigger_word if env else ""
        char_triggers = self._character_triggers(scene, episode)
        parts = [p for p in [env_trigger, shot.camera_angle, char_triggers, shot.action_start] if p]
        return ", ".join(parts) + self.QUALITY_SUFFIX

    def build_end_prompt(self, shot, scene, episode) -> str:
        env = episode.environments.get(scene.environment)
        env_trigger = env.trigger_word if env else ""
        char_triggers = self._character_triggers(scene, episode)
        parts = [p for p in [env_trigger, shot.camera_angle, char_triggers, shot.action_end] if p]
        return ", ".join(parts) + self.QUALITY_SUFFIX
