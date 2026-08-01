from __future__ import annotations

import hashlib
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any


GRAPHQL_URL = "https://api.github.com/graphql"
CONFIG_PATH = Path("config.json")

DEFAULT_CONFIG: dict[str, Any] = {
    "username": "",
    "output_path": "assets/github-stats.svg",
    "max_languages": 6,
    "exclude_languages": [],
    "theme": {
        "background": "#0d1117",
        "accent": "#58a6ff",
        "text": "#e6edf3",
        "muted": "#8b949e",
        "divider": "#21262d",
    },
    "labels": {
        "stats_title": "GitHub Stats",
        "languages_title": "Most Used Languages",
        "stars": "Total Stars Earned",
        "commits": "Total Commits",
        "pull_requests": "Total PRs",
        "issues": "Total Issues",
        "contributions_year": "Contributed (this year)",
        "total_contributions": "Total contributions",
        "current_streak": "Current streak",
        "longest_streak": "Longest streak",
    },
}


PROFILE_QUERY = """
query Profile($login: String!) {
  user(login: $login) {
    pullRequests(first: 1) {
      totalCount
    }

    issues(first: 1) {
      totalCount
    }

    contributionsCollection {
      contributionYears
    }
  }
}
"""


REPOSITORIES_QUERY = """
query Repositories(
  $login: String!
  $after: String
) {
  user(login: $login) {
    repositories(
      first: 100
      after: $after
      ownerAffiliations: OWNER
      privacy: PUBLIC
      isFork: false
      orderBy: {
        field: UPDATED_AT
        direction: DESC
      }
    ) {
      pageInfo {
        hasNextPage
        endCursor
      }

      nodes {
        stargazerCount

        languages(
          first: 20
          orderBy: {
            field: SIZE
            direction: DESC
          }
        ) {
          edges {
            size

            node {
              name
              color
            }
          }
        }
      }
    }
  }
}
"""


CONTRIBUTIONS_QUERY = """
query Contributions(
  $login: String!
  $from: DateTime!
  $to: DateTime!
) {
  user(login: $login) {
    contributionsCollection(
      from: $from
      to: $to
    ) {
      totalCommitContributions

      contributionCalendar {
        totalContributions

        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""


ICON_PATHS = {
    "star": """
      <path
        d="
          M12 2.5
          l2.8 5.7
          6.2.9
          -4.5 4.4
          1.1 6.2
          L12 16.8
          6.4 19.7
          l1.1-6.2
          L3 9.1
          l6.2-.9
          L12 2.5
          z
        "
      />
    """,

    "commit": """
      <path
        d="
          M12 4
          a8 8 0 1 1-5.7 2.3
        "
      />

      <path
        d="
          M4.2 3.8
          H8
          v3.8
        "
      />
    """,

    "pr": """
      <circle cx="7" cy="5" r="2"/>
      <circle cx="17" cy="19" r="2"/>
      <circle cx="17" cy="5" r="2"/>

      <path
        d="
          M7 7
          v10
          a2 2 0 0 0 2 2
          h6
        "
      />

      <path
        d="
          M15 5
          h-4
          a2 2 0 0 0-2 2
          v2
        "
      />
    """,

    "issue": """
      <circle cx="12" cy="12" r="8"/>

      <path
        d="
          M12 7.5
          v5
        "
      />

      <circle
        cx="12"
        cy="15.8"
        r="1"
        fill="currentColor"
        stroke="none"
      />
    """,

    "calendar": """
      <rect
        x="4"
        y="6"
        width="16"
        height="14"
        rx="1.8"
      />

      <path
        d="
          M4 10
          h16

          M8 3.8
          v4

          M16 3.8
          v4
        "
      />
    """,

    "people": """
      <circle cx="9" cy="9" r="2.3"/>
      <circle cx="15" cy="9" r="2.3"/>

      <path
        d="
          M5.5 18
          c.8-2.6 2.6-4 5.5-4
          s4.7 1.4 5.5 4
        "
      />

      <path
        d="
          M2.8 18
          c.6-1.8 1.7-2.8 3.2-3.3

          M21.2 18
          c-.6-1.8-1.7-2.8-3.2-3.3
        "
      />
    """,

    "flame": """
      <path
        d="
          M12 3.5
          c1.5 2.3 3.8 4 3.8 7.1

          A3.8 3.8 0 1 1 8.2 11

          c0-1.9 1-3.4 2.4-4.8

          .2 1.6.9 2.7 1.4 3.2

          .8-1.1 1-2.7 0-5.9
          z
        "
      />
    """,

    "trophy": """
      <path
        d="
          M8 5
          h8
          v3
          a4 4 0 0 1-8 0
          V5
          z
        "
      />

      <path
        d="
          M6 6
          H4
          a2 2 0 0 0 2 3

          M18 6
          h2
          a2 2 0 0 1-2 3
        "
      />

      <path
        d="
          M12 12
          v4

          M9 20
          h6
        "
      />
    """,
}


class ConfigurationError(ValueError):
    """Raised when config.json contains an invalid value."""


def deep_merge(
    defaults: dict[str, Any],
    override: dict[str, Any],
) -> dict[str, Any]:
    merged: dict[str, Any] = {}

    for key, default_value in defaults.items():
        override_value = override.get(
            key,
            default_value,
        )

        if isinstance(default_value, dict):
            if not isinstance(
                override_value,
                dict,
            ):
                raise ConfigurationError(
                    f"'{key}' must be a JSON object."
                )

            merged[key] = deep_merge(
                default_value,
                override_value,
            )
        else:
            merged[key] = override_value

    for key, value in override.items():
        if key not in merged:
            merged[key] = value

    return merged


def load_config(
    path: Path,
) -> dict[str, Any]:
    if not path.exists():
        raise ConfigurationError(
            f"{path} was not found."
        )

    try:
        raw = json.loads(
            path.read_text(
                encoding="utf-8",
            )
        )
    except json.JSONDecodeError as error:
        raise ConfigurationError(
            f"{path} is not valid JSON: {error}"
        ) from error

    if not isinstance(raw, dict):
        raise ConfigurationError(
            f"{path} must contain a JSON object."
        )

    config = deep_merge(
        DEFAULT_CONFIG,
        raw,
    )

    username = config["username"]

    if not isinstance(username, str):
        raise ConfigurationError(
            "'username' must be a string."
        )

    output_path = config["output_path"]

    if (
        not isinstance(output_path, str)
        or not output_path.strip()
    ):
        raise ConfigurationError(
            "'output_path' must be a non-empty string."
        )

    output = Path(output_path)

    if (
        output.is_absolute()
        or ".." in output.parts
    ):
        raise ConfigurationError(
            "'output_path' must stay inside "
            "the repository."
        )

    max_languages = config[
        "max_languages"
    ]

    if (
        not isinstance(max_languages, int)
        or isinstance(max_languages, bool)
        or not 1 <= max_languages <= 6
    ):
        raise ConfigurationError(
            "'max_languages' must be an "
            "integer from 1 to 6."
        )

    excluded = config[
        "exclude_languages"
    ]

    if (
        not isinstance(excluded, list)
        or not all(
            isinstance(item, str)
            for item in excluded
        )
    ):
        raise ConfigurationError(
            "'exclude_languages' must be "
            "a list of strings."
        )

    for section in (
        "theme",
        "labels",
    ):
        if not isinstance(
            config[section],
            dict,
        ):
            raise ConfigurationError(
                f"'{section}' must be "
                "a JSON object."
            )

    for key, value in config[
        "theme"
    ].items():
        if (
            not isinstance(value, str)
            or not value.strip()
        ):
            raise ConfigurationError(
                f"theme.{key} must be "
                "a non-empty string."
            )

    for key, value in config[
        "labels"
    ].items():
        if not isinstance(value, str):
            raise ConfigurationError(
                f"labels.{key} must be "
                "a string."
            )

    return config


def resolve_username(
    config: dict[str, Any],
) -> str:
    configured = config[
        "username"
    ].strip()

    if configured:
        return configured

    candidates = [
        os.getenv(
            "GITHUB_USERNAME",
            "",
        ),
        os.getenv(
            "GITHUB_REPOSITORY_OWNER",
            "",
        ),
    ]

    repository = os.getenv(
        "GITHUB_REPOSITORY",
        "",
    )

    if "/" in repository:
        candidates.append(
            repository.split(
                "/",
                1,
            )[0]
        )

    for candidate in candidates:
        candidate = candidate.strip()

        if candidate:
            return candidate

    raise ConfigurationError(
        "No GitHub username was found. "
        "Set 'username' in config.json "
        "or run through GitHub Actions."
    )


def esc(
    value: object,
) -> str:
    return html.escape(
        str(value),
        quote=True,
    )


def graphql_request(
    token: str,
    query: str,
    variables: dict[str, Any],
) -> dict[str, Any]:
    payload = json.dumps(
        {
            "query": query,
            "variables": variables,
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        GRAPHQL_URL,
        data=payload,
        method="POST",
        headers={
            "Authorization": (
                f"Bearer {token}"
            ),
            "Content-Type": (
                "application/json"
            ),
            "User-Agent": (
                "minimal-github-stats"
            ),
            "X-GitHub-Api-Version": (
                "2022-11-28"
            ),
        },
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=30,
        ) as response:
            result = json.loads(
                response.read().decode(
                    "utf-8"
                )
            )

    except urllib.error.HTTPError as error:
        body = error.read().decode(
            "utf-8",
            errors="replace",
        )

        raise RuntimeError(
            "GitHub API returned HTTP "
            f"{error.code}: {body}"
        ) from error

    except urllib.error.URLError as error:
        raise RuntimeError(
            "Could not contact the "
            f"GitHub API: {error}"
        ) from error

    errors = result.get("errors")

    if errors:
        messages = "; ".join(
            str(
                item.get(
                    "message",
                    item,
                )
            )
            for item in errors
        )

        raise RuntimeError(
            "GitHub GraphQL error: "
            f"{messages}"
        )

    data = result.get("data")

    if not isinstance(data, dict):
        raise RuntimeError(
            "GitHub returned an "
            "unexpected response."
        )

    return data


def fetch_repositories(
    token: str,
    username: str,
) -> list[dict[str, Any]]:
    repositories: list[
        dict[str, Any]
    ] = []

    cursor: str | None = None

    while True:
        data = graphql_request(
            token,
            REPOSITORIES_QUERY,
            {
                "login": username,
                "after": cursor,
            },
        )

        user = data.get("user")

        if user is None:
            raise RuntimeError(
                f"GitHub user '{username}' "
                "was not found."
            )

        connection = user[
            "repositories"
        ]

        repositories.extend(
            connection["nodes"]
        )

        page_info = connection[
            "pageInfo"
        ]

        if not page_info[
            "hasNextPage"
        ]:
            break

        cursor = page_info[
            "endCursor"
        ]

        if not cursor:
            break

    return repositories


def contribution_period(
    year: int,
    now: datetime,
) -> tuple[str, str]:
    start = datetime(
        year,
        1,
        1,
        tzinfo=timezone.utc,
    )

    if year == now.year:
        end = now
    else:
        end = datetime(
            year,
            12,
            31,
            23,
            59,
            59,
            tzinfo=timezone.utc,
        )

    return (
        start.isoformat(),
        end.isoformat(),
    )


def calculate_streaks(
    contribution_days: list[
        dict[str, Any]
    ],
) -> tuple[int, int]:
    counts: dict[
        date,
        int,
    ] = {}

    for item in contribution_days:
        current_date = (
            datetime.strptime(
                item["date"],
                "%Y-%m-%d",
            ).date()
        )

        counts[current_date] = int(
            item[
                "contributionCount"
            ]
        )

    if not counts:
        return 0, 0

    longest = 0
    running = 0

    for current_date in sorted(
        counts
    ):
        if counts[current_date] > 0:
            running += 1
            longest = max(
                longest,
                running,
            )
        else:
            running = 0

    cursor = datetime.now(
        timezone.utc
    ).date()

    if counts.get(cursor, 0) == 0:
        cursor -= timedelta(days=1)

    current = 0

    while counts.get(cursor, 0) > 0:
        current += 1
        cursor -= timedelta(days=1)

    return (
        current,
        longest,
    )


def collect_languages(
    repositories: list[
        dict[str, Any]
    ],
    excluded_languages: list[str],
    max_languages: int,
    fallback_color: str,
    muted_color: str,
) -> list[dict[str, Any]]:
    sizes: Counter[str] = Counter()
    colors: dict[str, str] = {}

    excluded = {
        item.casefold()
        for item in excluded_languages
    }

    for repository in repositories:
        language_edges = repository[
            "languages"
        ]["edges"]

        for edge in language_edges:
            name = edge[
                "node"
            ]["name"]

            if name.casefold() in excluded:
                continue

            size = int(
                edge["size"]
            )

            color = (
                edge["node"].get(
                    "color"
                )
                or fallback_color
            )

            sizes[name] += size
            colors[name] = color

    total = sum(
        sizes.values()
    )

    if total <= 0:
        return []

    ranked = sizes.most_common()

    if len(ranked) <= max_languages:
        displayed = [
            {
                "name": name,
                "size": size,
                "color": colors[name],
            }
            for name, size in ranked
        ]

    elif max_languages == 1:
        displayed = [
            {
                "name": "Other",
                "size": total,
                "color": muted_color,
            }
        ]

    else:
        displayed = [
            {
                "name": name,
                "size": size,
                "color": colors[name],
            }
            for name, size in ranked[
                : max_languages - 1
            ]
        ]

        other_size = sum(
            size
            for _, size in ranked[
                max_languages - 1 :
            ]
        )

        displayed.append(
            {
                "name": "Other",
                "size": other_size,
                "color": muted_color,
            }
        )

    for item in displayed:
        item["percentage"] = (
            item["size"]
            / total
            * 100
        )

    return displayed


def fetch_stats(
    token: str,
    username: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    now = datetime.now(
        timezone.utc
    )

    profile = graphql_request(
        token,
        PROFILE_QUERY,
        {
            "login": username,
        },
    )

    user = profile.get("user")

    if user is None:
        raise RuntimeError(
            f"GitHub user '{username}' "
            "was not found."
        )

    repositories = fetch_repositories(
        token,
        username,
    )

    years = sorted(
        {
            int(year)
            for year in user[
                "contributionsCollection"
            ]["contributionYears"]
        }
    )

    if now.year not in years:
        years.append(now.year)

    total_commits = 0
    total_contributions = 0
    contributed_this_year = 0

    all_days: list[
        dict[str, Any]
    ] = []

    for year in years:
        start, end = contribution_period(
            year,
            now,
        )

        contribution_data = (
            graphql_request(
                token,
                CONTRIBUTIONS_QUERY,
                {
                    "login": username,
                    "from": start,
                    "to": end,
                },
            )
        )

        contribution_user = (
            contribution_data.get(
                "user"
            )
        )

        if contribution_user is None:
            raise RuntimeError(
                f"GitHub user '{username}' "
                "was not found."
            )

        collection = contribution_user[
            "contributionsCollection"
        ]

        calendar = collection[
            "contributionCalendar"
        ]

        total_commits += int(
            collection[
                "totalCommitContributions"
            ]
        )

        yearly_total = int(
            calendar[
                "totalContributions"
            ]
        )

        total_contributions += (
            yearly_total
        )

        if year == now.year:
            contributed_this_year = (
                yearly_total
            )

        for week in calendar[
            "weeks"
        ]:
            all_days.extend(
                week[
                    "contributionDays"
                ]
            )

    current_streak, longest_streak = (
        calculate_streaks(
            all_days
        )
    )

    total_stars = sum(
        int(
            repository[
                "stargazerCount"
            ]
        )
        for repository in repositories
    )

    theme = config["theme"]

    return {
        "total_stars": total_stars,
        "total_commits": total_commits,
        "total_prs": int(
            user[
                "pullRequests"
            ]["totalCount"]
        ),
        "total_issues": int(
            user[
                "issues"
            ]["totalCount"]
        ),
        "contributed_this_year": (
            contributed_this_year
        ),
        "total_contributions": (
            total_contributions
        ),
        "current_streak": (
            current_streak
        ),
        "longest_streak": (
            longest_streak
        ),
        "languages": collect_languages(
            repositories,
            config[
                "exclude_languages"
            ],
            config[
                "max_languages"
            ],
            theme["accent"],
            theme["muted"],
        ),
    }


def icon(
    name: str,
    x: int,
    y: int,
    accent: str,
    scale: float = 1.0,
) -> str:
    return f"""
    <g
      transform="translate({x},{y}) scale({scale})"
      fill="none"
      stroke="{esc(accent)}"
      color="{esc(accent)}"
      stroke-width="1.9"
      stroke-linecap="round"
      stroke-linejoin="round">

      {ICON_PATHS[name]}

    </g>
    """


def stat_row(
    icon_name: str,
    label: str,
    value: int,
    y: int,
    left_x: int,
    value_x: int,
    accent: str,
) -> str:
    return f"""
    {icon(
        icon_name,
        left_x,
        y - 21,
        accent,
    )}

    <text
      x="{left_x + 38}"
      y="{y}"
      class="stat-label">
      {esc(label)}:
    </text>

    <text
      x="{value_x}"
      y="{y}"
      text-anchor="end"
      class="stat-value">
      {value:,}
    </text>
    """


def build_language_svg(
    languages: list[
        dict[str, Any]
    ],
    bar_x: int,
    bar_y: int,
    bar_width: int,
    bar_height: int,
    muted: str,
) -> tuple[str, str]:
    if not languages:
        languages = [
            {
                "name": (
                    "No language data"
                ),
                "percentage": 100.0,
                "color": muted,
            }
        ]

    segments: list[str] = []
    legend: list[str] = []

    cursor = float(bar_x)

    for index, language in enumerate(
        languages
    ):
        name = str(
            language["name"]
        )

        percentage = float(
            language[
                "percentage"
            ]
        )

        color = str(
            language["color"]
        )

        if index == len(languages) - 1:
            segment_width = (
                bar_x
                + bar_width
                - cursor
            )
        else:
            segment_width = (
                bar_width
                * percentage
                / 100
            )

        segments.append(
            f"""
            <rect
              x="{cursor:.2f}"
              y="{bar_y}"
              width="{max(segment_width, 1.5):.2f}"
              height="{bar_height}"
              fill="{esc(color)}"
            />
            """
        )

        cursor += segment_width

        column = index % 2
        row = index // 2

        legend_x = (
            bar_x
            + column * 200
        )

        legend_y = (
            bar_y
            + 34
            + row * 31
        )

        legend.append(
            f"""
            <circle
              cx="{legend_x + 5}"
              cy="{legend_y - 5}"
              r="4"
              fill="{esc(color)}"
            />

            <text
              x="{legend_x + 17}"
              y="{legend_y}"
              class="legend-label">
              {esc(name)}
            </text>

            <text
              x="{legend_x + 175}"
              y="{legend_y}"
              text-anchor="end"
              class="legend-value">
              {percentage:.1f}%
            </text>
            """
        )

    return (
        "\n".join(segments),
        "\n".join(legend),
    )


def build_fingerprint(
    username: str,
    stats: dict[str, Any],
    config: dict[str, Any],
) -> str:
    generator_hash = hashlib.sha256(
        Path(__file__).read_bytes()
    ).hexdigest()

    payload = {
        "username": username,
        "stats": stats,
        "theme": config["theme"],
        "labels": config["labels"],
        "max_languages": config[
            "max_languages"
        ],
        "exclude_languages": config[
            "exclude_languages"
        ],
        "generator_hash": generator_hash,
    }

    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(
        encoded
    ).hexdigest()


def existing_fingerprint(
    output_path: Path,
) -> str | None:
    if not output_path.exists():
        return None

    content = output_path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    match = re.search(
        r'data-fingerprint="([0-9a-f]{64})"',
        content,
    )

    if match is None:
        return None

    return match.group(1)


def build_svg(
    username: str,
    stats: dict[str, Any],
    config: dict[str, Any],
    fingerprint: str,
) -> str:
    width = 1000
    height = 340

    left_x = 34
    left_value_x = 455
    right_x = 535
    title_y = 56

    row_y = [
        92,
        120,
        148,
        176,
        204,
    ]

    bar_x = right_x
    bar_y = 98
    bar_width = 405
    bar_height = 7

    theme = config["theme"]
    labels = config["labels"]

    background = theme[
        "background"
    ]

    accent = theme["accent"]
    text = theme["text"]
    muted = theme["muted"]
    divider = theme["divider"]

    (
        language_segments,
        language_legend,
    ) = build_language_svg(
        stats["languages"],
        bar_x,
        bar_y,
        bar_width,
        bar_height,
        muted,
    )

    rows = "\n".join(
        [
            stat_row(
                "star",
                labels["stars"],
                stats["total_stars"],
                row_y[0],
                left_x,
                left_value_x,
                accent,
            ),

            stat_row(
                "commit",
                labels["commits"],
                stats[
                    "total_commits"
                ],
                row_y[1],
                left_x,
                left_value_x,
                accent,
            ),

            stat_row(
                "pr",
                labels[
                    "pull_requests"
                ],
                stats["total_prs"],
                row_y[2],
                left_x,
                left_value_x,
                accent,
            ),

            stat_row(
                "issue",
                labels["issues"],
                stats[
                    "total_issues"
                ],
                row_y[3],
                left_x,
                left_value_x,
                accent,
            ),

            stat_row(
                "calendar",
                labels[
                    "contributions_year"
                ],
                stats[
                    "contributed_this_year"
                ],
                row_y[4],
                left_x,
                left_value_x,
                accent,
            ),
        ]
    )

    updated = datetime.now(
        timezone.utc
    ).strftime(
        "%Y-%m-%d %H:%M UTC"
    )

    return f"""<svg
  xmlns="http://www.w3.org/2000/svg"
  width="{width}"
  height="{height}"
  viewBox="0 0 {width} {height}"
  role="img"
  aria-labelledby="title description"
  data-fingerprint="{fingerprint}">

  <title id="title">
    {esc(username)} GitHub statistics
  </title>

  <desc id="description">
    Automatically generated GitHub statistics,
    language usage and contribution streaks.
  </desc>

  <defs>
    <clipPath id="language-bar-clip">
      <rect
        x="{bar_x}"
        y="{bar_y}"
        width="{bar_width}"
        height="{bar_height}"
        rx="{bar_height / 2}"
      />
    </clipPath>
  </defs>

  <style>
    .section-title {{
      font:
        400 18px
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;

      fill: {esc(accent)};
    }}

    .stat-label,
    .stat-value {{
      font:
        700 14px
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;

      fill: {esc(text)};
    }}

    .legend-label {{
      font:
        400 12px
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;

      fill: {esc(text)};
    }}

    .legend-value {{
      font:
        700 12px
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;

      fill: {esc(text)};
    }}

    .metric-number {{
      font:
        700 24px
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;

      fill: {esc(accent)};
    }}

    .metric-label {{
      font:
        600 13px
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;

      fill: {esc(text)};
    }}

    .updated {{
      font:
        400 11px
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;

      fill: {esc(muted)};
    }}
  </style>

  <rect
    width="{width}"
    height="{height}"
    rx="16"
    fill="{esc(background)}"
  />

  <text
    x="{left_x + 1}"
    y="{title_y}"
    class="section-title">
    {esc(labels["stats_title"])}
  </text>

  <text
    x="{right_x}"
    y="{title_y}"
    class="section-title">
    {esc(labels["languages_title"])}
  </text>

  <line
    x1="500"
    y1="34"
    x2="500"
    y2="218"
    stroke="{esc(divider)}"
    stroke-width="1"
  />

  {rows}

  <rect
    x="{bar_x}"
    y="{bar_y}"
    width="{bar_width}"
    height="{bar_height}"
    rx="{bar_height / 2}"
    fill="{esc(divider)}"
  />

  <g clip-path="url(#language-bar-clip)">
    {language_segments}
  </g>

  {language_legend}

  <line
    x1="333"
    y1="232"
    x2="333"
    y2="315"
    stroke="{esc(divider)}"
    stroke-width="1"
  />

  <line
    x1="667"
    y1="232"
    x2="667"
    y2="315"
    stroke="{esc(divider)}"
    stroke-width="1"
  />

  {icon(
      "people",
      149,
      226,
      accent,
      1.5,
  )}

  <text
    x="167"
    y="278"
    text-anchor="middle"
    class="metric-number">
    {stats["total_contributions"]:,}
  </text>

  <text
    x="167"
    y="307"
    text-anchor="middle"
    class="metric-label">
    {esc(labels["total_contributions"])}
  </text>

  {icon(
      "flame",
      482,
      226,
      accent,
      1.5,
  )}

  <text
    x="500"
    y="278"
    text-anchor="middle"
    class="metric-number">
    {stats["current_streak"]}
  </text>

  <text
    x="500"
    y="307"
    text-anchor="middle"
    class="metric-label">
    {esc(labels["current_streak"])}
  </text>

  {icon(
      "trophy",
      816,
      226,
      accent,
      1.5,
  )}

  <text
    x="834"
    y="278"
    text-anchor="middle"
    class="metric-number">
    {stats["longest_streak"]}
  </text>

  <text
    x="834"
    y="307"
    text-anchor="middle"
    class="metric-label">
    {esc(labels["longest_streak"])}
  </text>

  <text
    x="950"
    y="327"
    text-anchor="end"
    class="updated">
    Updated {esc(updated)}
  </text>
</svg>
"""


def main() -> int:
    try:
        config = load_config(
            CONFIG_PATH
        )

        username = resolve_username(
            config
        )

        token = os.getenv(
            "GITHUB_TOKEN",
            "",
        ).strip()

        if not token:
            raise RuntimeError(
                "GITHUB_TOKEN is missing. "
                "Run this script through the "
                "included GitHub Actions workflow "
                "or export a token locally."
            )

        output_path = Path(
            config["output_path"]
        )

        stats = fetch_stats(
            token,
            username,
            config,
        )

        fingerprint = build_fingerprint(
            username,
            stats,
            config,
        )

        if (
            existing_fingerprint(
                output_path
            )
            == fingerprint
        ):
            print(
                "Statistics have not changed; "
                "the SVG was left untouched."
            )

            return 0

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path.write_text(
            build_svg(
                username,
                stats,
                config,
                fingerprint,
            ),
            encoding="utf-8",
        )

        print(
            f"Updated {output_path} "
            f"for {username}."
        )

        return 0

    except (
        ConfigurationError,
        RuntimeError,
        OSError,
    ) as error:
        print(
            f"Error: {error}",
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
