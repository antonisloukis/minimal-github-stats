from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = ROOT / "scripts" / "generate_stats.py"

SPEC = importlib.util.spec_from_file_location(
    "generate_stats",
    GENERATOR_PATH,
)

if SPEC is None or SPEC.loader is None:
    raise RuntimeError(
        "Could not load scripts/generate_stats.py"
    )

generator = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = generator
SPEC.loader.exec_module(generator)


class ConfigurationTests(unittest.TestCase):
    def write_config(
        self,
        directory: str,
        value: dict,
    ) -> Path:
        path = Path(directory) / "config.json"

        path.write_text(
            json.dumps(value),
            encoding="utf-8",
        )

        return path

    def test_load_config_merges_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_config(
                directory,
                {
                    "max_languages": 3,
                    "theme": {
                        "accent": "#ffffff",
                    },
                },
            )

            config = generator.load_config(path)

        self.assertEqual(
            config["max_languages"],
            3,
        )

        self.assertEqual(
            config["theme"]["accent"],
            "#ffffff",
        )

        self.assertEqual(
            config["theme"]["background"],
            generator.DEFAULT_CONFIG[
                "theme"
            ]["background"],
        )

        self.assertEqual(
            config["username"],
            "",
        )

    def test_eight_languages_are_allowed(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_config(
                directory,
                {
                    "max_languages": 8,
                },
            )

            config = generator.load_config(path)

        self.assertEqual(
            config["max_languages"],
            8,
        )

    def test_invalid_language_limit_is_rejected(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_config(
                directory,
                {
                    "max_languages": 9,
                },
            )

            with self.assertRaises(
                generator.ConfigurationError
            ):
                generator.load_config(path)

    def test_output_path_cannot_leave_repository(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_config(
                directory,
                {
                    "output_path": (
                        "../outside.svg"
                    ),
                },
            )

            with self.assertRaises(
                generator.ConfigurationError
            ):
                generator.load_config(path)

    def test_repository_owner_is_detected(
        self,
    ) -> None:
        config = generator.deep_merge(
            generator.DEFAULT_CONFIG,
            {},
        )

        environment = {
            "GITHUB_REPOSITORY_OWNER": (
                "example-user"
            ),
        }

        with patch.dict(
            os.environ,
            environment,
            clear=True,
        ):
            username = (
                generator.resolve_username(
                    config
                )
            )

        self.assertEqual(
            username,
            "example-user",
        )

    def test_repository_name_can_supply_owner(
        self,
    ) -> None:
        config = generator.deep_merge(
            generator.DEFAULT_CONFIG,
            {},
        )

        environment = {
            "GITHUB_REPOSITORY": (
                "example-user/"
                "minimal-github-stats"
            ),
        }

        with patch.dict(
            os.environ,
            environment,
            clear=True,
        ):
            username = (
                generator.resolve_username(
                    config
                )
            )

        self.assertEqual(
            username,
            "example-user",
        )


class StreakTests(unittest.TestCase):
    def test_current_and_longest_streaks(
        self,
    ) -> None:
        today = datetime.now(
            timezone.utc
        ).date()

        counts = [
            (6, 1),
            (5, 1),
            (4, 0),
            (3, 2),
            (2, 1),
            (1, 3),
            (0, 1),
        ]

        contribution_days = [
            {
                "date": (
                    today
                    - timedelta(days=offset)
                ).isoformat(),
                "contributionCount": count,
            }
            for offset, count in counts
        ]

        current, longest = (
            generator.calculate_streaks(
                contribution_days
            )
        )

        self.assertEqual(current, 4)
        self.assertEqual(longest, 4)

    def test_empty_contributions_have_no_streak(
        self,
    ) -> None:
        current, longest = (
            generator.calculate_streaks([])
        )

        self.assertEqual(current, 0)
        self.assertEqual(longest, 0)


class LanguageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repositories = [
            {
                "stargazerCount": 0,
                "languages": {
                    "edges": [
                        {
                            "size": 800,
                            "node": {
                                "name": "Python",
                                "color": "#3572A5",
                            },
                        },
                        {
                            "size": 200,
                            "node": {
                                "name": "HTML",
                                "color": "#e34c26",
                            },
                        },
                    ]
                },
            },
            {
                "stargazerCount": 0,
                "languages": {
                    "edges": [
                        {
                            "size": 200,
                            "node": {
                                "name": "Python",
                                "color": "#3572A5",
                            },
                        },
                        {
                            "size": 500,
                            "node": {
                                "name": "Go",
                                "color": "#00ADD8",
                            },
                        },
                        {
                            "size": 300,
                            "node": {
                                "name": "Shell",
                                "color": None,
                            },
                        },
                    ]
                },
            },
        ]

    def test_languages_are_aggregated(
        self,
    ) -> None:
        languages = (
            generator.collect_languages(
                self.repositories,
                excluded_languages=[],
                max_languages=6,
                fallback_color="#58a6ff",
                muted_color="#8b949e",
            )
        )

        self.assertEqual(
            languages[0]["name"],
            "Python",
        )

        self.assertEqual(
            languages[0]["size"],
            1000,
        )

    def test_exclusion_is_case_insensitive(
        self,
    ) -> None:
        languages = (
            generator.collect_languages(
                self.repositories,
                excluded_languages=[
                    "html"
                ],
                max_languages=6,
                fallback_color="#58a6ff",
                muted_color="#8b949e",
            )
        )

        names = [
            language["name"]
            for language in languages
        ]

        self.assertNotIn(
            "HTML",
            names,
        )

    def test_remaining_languages_are_grouped(
        self,
    ) -> None:
        languages = (
            generator.collect_languages(
                self.repositories,
                excluded_languages=[
                    "HTML"
                ],
                max_languages=2,
                fallback_color="#58a6ff",
                muted_color="#8b949e",
            )
        )

        self.assertEqual(
            [
                language["name"]
                for language in languages
            ],
            [
                "Python",
                "Other",
            ],
        )

        self.assertEqual(
            languages[1]["size"],
            800,
        )

        total_percentage = sum(
            language["percentage"]
            for language in languages
        )

        self.assertAlmostEqual(
            total_percentage,
            100.0,
        )

    def test_no_language_data_returns_empty_list(
        self,
    ) -> None:
        languages = (
            generator.collect_languages(
                [],
                excluded_languages=[],
                max_languages=6,
                fallback_color="#58a6ff",
                muted_color="#8b949e",
            )
        )

        self.assertEqual(
            languages,
            [],
        )


class SvgTests(unittest.TestCase):
    def make_stats(self) -> dict:
        return {
            "total_stars": 10,
            "total_commits": 100,
            "total_prs": 20,
            "total_issues": 5,
            "contributed_this_year": 50,
            "total_contributions": 250,
            "current_streak": 4,
            "longest_streak": 15,
            "languages": [
                {
                    "name": "Python",
                    "size": 800,
                    "color": "#3572A5",
                    "percentage": 80.0,
                },
                {
                    "name": "Go",
                    "size": 200,
                    "color": "#00ADD8",
                    "percentage": 20.0,
                },
            ],
        }

    def test_language_legend_supports_eight_entries(
        self,
    ) -> None:
        languages = [
            {
                "name": f"Language {index}",
                "percentage": 12.5,
                "color": "#58a6ff",
            }
            for index in range(1, 9)
        ]

        _, legend = generator.build_language_svg(
            languages,
            bar_x=535,
            bar_y=98,
            bar_width=405,
            bar_height=7,
            muted="#8b949e",
        )

        self.assertEqual(
            legend.count("<circle"),
            8,
        )

        self.assertEqual(
            legend.count('cx="540"'),
            4,
        )

        self.assertEqual(
            legend.count('cx="740"'),
            4,
        )

    def test_svg_contains_expected_metadata(
        self,
    ) -> None:
        config = generator.deep_merge(
            generator.DEFAULT_CONFIG,
            {},
        )

        fingerprint = "a" * 64

        svg = generator.build_svg(
            "example-user",
            self.make_stats(),
            config,
            fingerprint,
        )

        self.assertIn(
            'role="img"',
            svg,
        )

        self.assertIn(
            (
                'data-fingerprint="'
                f'{fingerprint}"'
            ),
            svg,
        )

        self.assertIn(
            "example-user GitHub statistics",
            svg,
        )

        self.assertIn(
            "Python",
            svg,
        )

    def test_label_text_is_escaped(
        self,
    ) -> None:
        config = generator.deep_merge(
            generator.DEFAULT_CONFIG,
            {
                "labels": {
                    "stats_title": (
                        "Stats <unsafe>"
                    ),
                },
            },
        )

        svg = generator.build_svg(
            "example-user",
            self.make_stats(),
            config,
            "b" * 64,
        )

        self.assertIn(
            "Stats &lt;unsafe&gt;",
            svg,
        )

        self.assertNotIn(
            "Stats <unsafe>",
            svg,
        )

    def test_existing_fingerprint_is_read(
        self,
    ) -> None:
        fingerprint = "c" * 64

        with tempfile.TemporaryDirectory() as directory:
            output = (
                Path(directory)
                / "stats.svg"
            )

            output.write_text(
                (
                    "<svg "
                    f'data-fingerprint="{fingerprint}"'
                    "></svg>"
                ),
                encoding="utf-8",
            )

            result = (
                generator.existing_fingerprint(
                    output
                )
            )

        self.assertEqual(
            result,
            fingerprint,
        )


if __name__ == "__main__":
    unittest.main()
