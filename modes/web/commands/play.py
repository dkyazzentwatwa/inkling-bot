"""Play and energy commands."""
import asyncio
import time
from typing import Dict, Any

from core.personality import Mood
from core.progression import XPSource
from . import CommandHandler


class PlayCommands(CommandHandler):
    """Handlers for play commands (/walk, /dance, /exercise, /play, /pet, /rest, /energy)."""

    async def _play_action_web(
        self,
        action_name: str,
        emote_text: str,
        mood: Mood,
        intensity: float,
        faces: list,
        xp_source: XPSource,
    ) -> tuple:
        """
        Execute a play action with animation and rewards (web version).

        Returns:
            (xp_gained, energy_change) tuple
        """
        # Update interaction time
        self.personality._last_interaction = time.time()

        # Show animation on display
        if self.display:
            for i, face in enumerate(faces):
                is_last = (i == len(faces) - 1)
                text = f"{action_name.title()}!"
                await self.display.update(
                    face=face,
                    text=text,
                    force=True,
                )
                if not is_last:
                    await asyncio.sleep(0.8)

        # Boost mood and intensity
        old_mood = self.personality.mood.current
        old_intensity = self.personality.mood.intensity
        self.personality.mood.set_mood(mood, intensity)

        # Award XP
        xp_amounts = {
            XPSource.PLAY_WALK: 3,
            XPSource.PLAY_DANCE: 5,
            XPSource.PLAY_EXERCISE: 5,
            XPSource.PLAY_GENERAL: 4,
            XPSource.PLAY_REST: 2,
            XPSource.PLAY_PET: 3,
        }
        awarded, xp_gained = self.personality.progression.award_xp(
            xp_source,
            xp_amounts.get(xp_source, 3)
        )

        # Calculate energy change
        old_energy = old_mood.energy * old_intensity
        new_energy = self.personality.energy
        energy_change = new_energy - old_energy

        return (xp_gained if awarded else 0, energy_change)

    def walk(self) -> Dict[str, Any]:
        """Go for a walk."""
        xp_gained, energy_change = asyncio.run_coroutine_threadsafe(
            self._play_action_web(
                "walk",
                "goes for a walk",
                Mood.CURIOUS,
                0.7,
                ["look_l", "look_r", "happy"],
                XPSource.PLAY_WALK,
            ),
            self._loop
        ).result(timeout=5.0)

        response = f"*{self.personality.name} goes for a walk around the neighborhood*\n\n"
        if xp_gained > 0:
            response += f"✨ +{xp_gained} XP | Energy {energy_change:+.0%}"
        else:
            response += f"Energy {energy_change:+.0%}"

        return {
            "response": response,
            "face": "happy",
        }

    def dance(self) -> Dict[str, Any]:
        """Dance around."""
        xp_gained, energy_change = asyncio.run_coroutine_threadsafe(
            self._play_action_web(
                "dance",
                "dances enthusiastically",
                Mood.EXCITED,
                0.9,
                ["excited", "love", "wink", "excited"],
                XPSource.PLAY_DANCE,
            ),
            self._loop
        ).result(timeout=5.0)

        response = f"*{self.personality.name} dances enthusiastically*\n\n"
        if xp_gained > 0:
            response += f"✨ +{xp_gained} XP | Energy {energy_change:+.0%}"
        else:
            response += f"Energy {energy_change:+.0%}"

        return {
            "response": response,
            "face": "excited",
        }

    def exercise(self) -> Dict[str, Any]:
        """Exercise and stretch."""
        xp_gained, energy_change = asyncio.run_coroutine_threadsafe(
            self._play_action_web(
                "exercise",
                "does some stretches",
                Mood.HAPPY,
                0.8,
                ["working", "intense", "awake", "success"],
                XPSource.PLAY_EXERCISE,
            ),
            self._loop
        ).result(timeout=5.0)

        response = f"*{self.personality.name} does some stretches and exercises*\n\n"
        if xp_gained > 0:
            response += f"✨ +{xp_gained} XP | Energy {energy_change:+.0%}"
        else:
            response += f"Energy {energy_change:+.0%}"

        return {
            "response": response,
            "face": "success",
        }

    def play(self) -> Dict[str, Any]:
        """Play with a toy."""
        xp_gained, energy_change = asyncio.run_coroutine_threadsafe(
            self._play_action_web(
                "play",
                "plays with a toy",
                Mood.HAPPY,
                0.8,
                ["excited", "happy", "wink"],
                XPSource.PLAY_GENERAL,
            ),
            self._loop
        ).result(timeout=5.0)

        response = f"*{self.personality.name} plays with a toy*\n\n"
        if xp_gained > 0:
            response += f"✨ +{xp_gained} XP | Energy {energy_change:+.0%}"
        else:
            response += f"Energy {energy_change:+.0%}"

        return {
            "response": response,
            "face": "happy",
        }

    def pet(self) -> Dict[str, Any]:
        """Get petted."""
        xp_gained, energy_change = asyncio.run_coroutine_threadsafe(
            self._play_action_web(
                "pet",
                "enjoys being petted",
                Mood.GRATEFUL,
                0.7,
                ["love", "happy", "grateful"],
                XPSource.PLAY_PET,
            ),
            self._loop
        ).result(timeout=5.0)

        response = f"*{self.personality.name} enjoys being petted*\n\n"
        if xp_gained > 0:
            response += f"✨ +{xp_gained} XP | Energy {energy_change:+.0%}"
        else:
            response += f"Energy {energy_change:+.0%}"

        return {
            "response": response,
            "face": "grateful",
        }

    def rest(self) -> Dict[str, Any]:
        """Take a short rest."""
        xp_gained, energy_change = asyncio.run_coroutine_threadsafe(
            self._play_action_web(
                "rest",
                "takes a short rest",
                Mood.COOL,
                0.4,
                ["cool", "sleep", "sleepy"],
                XPSource.PLAY_REST,
            ),
            self._loop
        ).result(timeout=5.0)

        response = f"*{self.personality.name} takes a short rest*\n\n"
        if xp_gained > 0:
            response += f"✨ +{xp_gained} XP | Energy {energy_change:+.0%}"
        else:
            response += f"Energy {energy_change:+.0%}"

        return {
            "response": response,
            "face": "sleepy",
        }

    def energy(self) -> Dict[str, Any]:
        """Show energy level."""
        energy = self.personality.energy
        mood = self.personality.mood.current.value
        intensity = self.personality.mood.intensity

        # Create visual bar
        bar_filled = int(energy * 10)
        bar = "█" * bar_filled + "░" * (10 - bar_filled)

        return {
            "response": f"Energy: [{bar}] {energy:.0%}\n\nMood: {mood.title()} (intensity: {intensity:.0%})\nMood base energy: {self.personality.mood.current.energy:.0%}\n\n*Tip: Play commands (/walk, /dance, /exercise) boost energy!*",
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }
