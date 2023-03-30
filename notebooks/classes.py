"""Relevant classes for web scraping game histories."""

import re
from abc import ABC, abstractmethod
from dataclasses import InitVar, dataclass, field
from typing import Any, ClassVar

import pandas as pd
from pandas import DataFrame, Series


# ---------------------------------- GAMER ---------------------------------------------
@dataclass
class Gamer:
    """Gamer class containing gamer id information."""

    _name: str
    _gamer: str
    _url: str = field(init=False)
    url_base: InitVar[str] = "https://mlb22.theshow.com/universal_profiles"
    url_infix: InitVar[str] = "game_history?page="
    url_suffix: InitVar[str] = "&mode=ARENA&subdomain=mlb22"

    def __post_init__(self, url_base, url_infix, url_suffix) -> None:
        """Construct the gamer url."""
        self._url = f"{url_base}/{self._gamer}/{url_infix}1{url_suffix}"

    def __str__(self) -> str:
        """Provide pretty response for Gamer instance."""
        return (
            f"     Name: {self._name}\n"
            f"Gamer Tag: {self._gamer}\n"
            f"Gamer URL: {self._url}"
        )

    @property
    def name(self) -> str:
        return self._name

    @property
    def gamer(self) -> str:
        return self._gamer

    @property
    def url(self) -> str:
        return self._url


# ---------------------------------- GAME LOG ------------------------------------------
@dataclass
class GameLog:
    """Game log class."""

    batters: Series
    # pitchers: Series
    html: str
    patterns: ClassVar[dict[str, re.Pattern]] = {
        "game_difficulty_re": re.compile(
            r"Hitting Difficulty is (?P<difficulty>[\w -]+)"
        ),
        "inning_number_re": re.compile(r"^(?P<inning>Inning \d+):"),
        "inning_stats_re": re.compile(r"(?P<stat>[\w ]+): (?P<value>\d+) ?"),
        "inning_stats_full_re": re.compile(
            r"Runs: \d+ Hits: \d+ Walks: \d+ Errors: \d+ Pitches: \d+( Runners Left On: \d+)?"
        ),
        "parenthesis_re": re.compile(r"\s\([\w %-]+\)"),
        "period_pattern": re.compile(r"\.{1}"),
        "team_re": re.compile(r"^(?P<team>.+) batting\."),
    }

    def __post_init__(self) -> None:
        updated_html = self.remove_trivial_text()
        self.log_split, self.misc = self.partition_and_remove_tags(updated_html)
        self.log = self.join_log_split()
        self.difficulty = self.retrieve_difficulty()
        self.batters_clean = self.clean_batters()
        (
            self.batters_to_replace,
            self.batters_replacements,
        ) = self.create_replacement_series()
        self.inning_stats = self.process_inning_stats()

    def remove_trivial_text(self) -> str:
        """Remove leading and trailing non <br> tag html, asterisks, and parentheses."""
        updated_html = self.html.replace(
            '<div class="section-block">\n<h3>Game Log</h3>\n', ""
        )
        updated_html = updated_html.replace("\n</div>", "")
        updated_html = updated_html.replace("*", "")
        updated_html = type(self).patterns["parenthesis_re"].sub("", updated_html)
        return updated_html

    def partition_and_remove_tags(self, html: str) -> tuple[list, str]:
        """Partition html into game log and miscellaneous data and remove <br> tags."""

        def partition(html: str) -> tuple[str, str]:
            """Partition html into game log and miscellaneous data."""
            partition = html.partition("Game Log Legend")
            return partition[0], partition[1] + partition[2]

        def remove_tags(html: str) -> list:
            """Remove tags by splitting the log text on <br> tags."""
            text_split = html.split("<br>")
            # Remove any empty strings
            text_split = [line.strip() for line in text_split if line]
            return text_split

        log, misc = partition(html)
        log_split = remove_tags(log)
        misc_split = remove_tags(misc)
        misc = " ".join(misc_split)
        return log_split, misc

    def join_log_split(self):
        """Join a game log that had been split previously to form one string."""
        log_split_filtered = [
            line
            for line in self.log_split
            if not type(self).patterns["inning_stats_full_re"].match(line)
        ]
        return " ".join(log_split_filtered)

    def retrieve_difficulty(self) -> str | None:
        """Retrieve the game difficulty based on the batting difficulty."""
        match = type(self).patterns["game_difficulty_re"].search(self.misc)
        if match:
            return match.group("difficulty")
        else:
            return None

    def clean_batters(self) -> Series:
        """Remove the periods from any names that have them."""
        return self.batters.str.replace(
            type(self).patterns["period_pattern"].pattern, "", regex=True
        )

    def create_replacement_series(self) -> tuple[Series, Series]:
        """Create the Series containing names to be replaced and their replacements."""
        batters_to_replace = self.batters[
            self.batters.str.contains(type(self).patterns["period_pattern"].pattern)
        ]
        batters_replacements = batters_to_replace.str.replace(
            type(self).patterns["period_pattern"].pattern, "", regex=True
        )
        return batters_to_replace, batters_replacements

    def process_inning_stats(self) -> dict[str, dict[str, dict[str, int]]]:
        """Separate, by inning and team, the inning stat lines from the game."""
        inning_stats: dict[str, dict[str, dict[str, int]]] = {}

        for line in self.log_split:
            inning_number_match = type(self).patterns["inning_number_re"].match(line)
            team_match = type(self).patterns["team_re"].match(line)
            inning_stats_matches = type(self).patterns["inning_stats_re"].finditer(line)

            if inning_number_match:
                inning = inning_number_match.group("inning").replace(":", "")
                inning_stats[inning] = {}

            elif team_match:
                team = team_match.group("team")
                inning_stats[inning][team] = {}

            elif inning_stats_matches:
                inning_stats[inning][team] = {
                    match.group("stat"): int(match.group("value"))
                    for match in inning_stats_matches
                }
        return inning_stats


# ---------------------------------- HOME AWAY DATA ------------------------------------
@dataclass
class HomeAwayData:
    """HomeAwayData class."""

    away: Any
    home: Any

    def __getitem__(self, attribute):
        """Make the class subscriptable."""
        return getattr(self, attribute)


# ---------------------------------- LINESCORE -----------------------------------------
@dataclass
class Linescore:
    """Linescore class."""

    linescore_raw: DataFrame
    teams: HomeAwayData = field(init=False)
    gamers: HomeAwayData = field(init=False)
    results: HomeAwayData = field(init=False)

    def __post_init__(self) -> None:
        self.linescore = self.clean_linescore()
        self.teams = HomeAwayData(
            self.linescore.teams.loc["away"], self.linescore.teams.loc["home"]
        )
        self.gamers = HomeAwayData(
            self.linescore.gamers.loc["away"], self.linescore.gamers.loc["home"]
        )
        self.results = HomeAwayData(
            self.linescore.results.loc["away"], self.linescore.results.loc["home"]
        )

    def clean_linescore(self) -> DataFrame:
        """Clean raw linescore."""
        linescore = self.linescore_raw.copy()

        linescore = linescore.drop(columns="0")
        linescore.iloc[0, :3] = pd.Series(["teams", "gamers", "results"])
        linescore.columns = pd.Index(linescore.iloc[0])
        linescore = linescore.drop(index=0)
        linescore.insert(loc=0, column="gamers", value=linescore.pop("gamers"))
        linescore.columns = linescore.columns.astype(str)

        linescore.index = pd.Index(["away", "home"])

        cols_to_numeric = ["R", "H", "E"]
        linescore[cols_to_numeric] = linescore[cols_to_numeric].apply(pd.to_numeric)
        linescore.index.name = None

        return linescore


# ---------------------------------- BOXSCORE ------------------------------------------
@dataclass
class Boxscore(ABC):
    """Boxscore class. Not meant to be instantiated directly."""

    boxscore_raw: HomeAwayData

    @abstractmethod
    def clean_boxscore(self, boxscore_raw: DataFrame) -> Any:
        """Clean the raw boxscore."""
        pass

    @abstractmethod
    def get_totals(self):
        """Retrieve the stats totals for the given boxscore."""
        pass


# ---------------------------------- BATTING BOXSCORE ----------------------------------
@dataclass
class BattingBoxscore(Boxscore):
    """Batting Boxscore class."""

    patterns: ClassVar[dict[str, re.Pattern]] = {
        "batter_names_re": re.compile(r"([a-z]-)?(?P<name>.+),"),
    }

    def __post_init__(self) -> None:
        away_boxscore = self.clean_boxscore(self.boxscore_raw.away)
        home_boxscore = self.clean_boxscore(self.boxscore_raw.home)
        self.boxscore = HomeAwayData(away_boxscore, home_boxscore)

    def clean_boxscore(self, boxscore_raw: DataFrame) -> DataFrame:
        """Clean the raw batting boxscore."""
        boxscore = boxscore_raw.copy()
        boxscore = boxscore.drop(columns="AVG")

        # Clean the batter names using the `names_re` pattern
        hitters = boxscore.iloc[:-1, boxscore.columns.get_loc("Batter")]
        boxscore.iloc[:-1, boxscore.columns.get_loc("Batter")] = hitters.str.extract(
            type(self).patterns["batter_names_re"].pattern
        )["name"]

        boxscore = boxscore.set_index("Batter")
        boxscore.index.name = None

        return boxscore

    def get_totals(self):
        """Retrieve the batting stats totals."""
        pass

    def get_player_list(self):
        """Retrieve the list of batters."""
        pass


# ---------------------------------- PITCHING BOXSCORE ---------------------------------
@dataclass
class PitchingBoxscore(Boxscore):
    """Pitching Boxscore class."""

    pitching_decisions: ClassVar[list[str]] = ["W", "L", "S", "BS", "H"]
    patterns: ClassVar[dict[str, re.Pattern]] = {
        "abbreviated_re": re.compile(r"(?P<name>.+)(\.{3})"),
        "ellipsis_re": re.compile(r"\.{3}"),
        "pitching_stat_re": re.compile(r"(?P<parenthesis> \((?P<stat>\w+)\))"),
    }

    def __post_init__(self) -> None:
        away_boxscore, away_abbreviated = self.clean_boxscore(self.boxscore_raw.away)
        home_boxscore, home_abbreviated = self.clean_boxscore(self.boxscore_raw.home)
        self.boxscore = HomeAwayData(away_boxscore, home_boxscore)
        self.abbreviated_names = HomeAwayData(away_abbreviated, home_abbreviated)

    def clean_boxscore(self, boxscore_raw: DataFrame) -> tuple[DataFrame, Series]:
        """Clean the raw pitching boxscore."""
        boxscore = boxscore_raw.copy()
        boxscore = boxscore.drop(columns="ERA")

        # Generate extended pitching stats from the game decisions in parentheses.
        parentheses_groups = boxscore["Pitcher"].str.extract(
            type(self).patterns["pitching_stat_re"].pattern
        )
        extended_stats = pd.get_dummies(parentheses_groups["stat"])

        # Add in the game decisions that were not awarded in this game as columns of
        # zeros.
        for cat in type(self).pitching_decisions:
            if cat not in extended_stats.columns:
                extended_stats[cat] = 0
        # Reorder the columns so that the extended stats are in a uniform order.
        extended_stats = extended_stats[type(self).pitching_decisions]

        # Tally the totals for the newly added pitch decision stats.
        extended_stats.iloc[len(extended_stats) - 1] = extended_stats.sum()

        # Concatenate the extended stats onto the boxscore.
        boxscore = pd.concat([boxscore, extended_stats], axis=1)

        # Remove the parentheses game decisions.
        boxscore["Pitcher"] = boxscore["Pitcher"].str.replace(
            type(self).patterns["pitching_stat_re"].pattern, "", regex=True
        )

        # Collect any
        abbreviated_names = boxscore.Pitcher.str.extract(
            type(self).patterns["abbreviated_re"].pattern
        )["name"]
        abbreviated_names = abbreviated_names[abbreviated_names.notna()]

        boxscore["Pitcher"] = boxscore["Pitcher"].str.replace(
            type(self).patterns["ellipsis_re"].pattern, "", regex=True
        )

        boxscore = boxscore.set_index("Pitcher")
        boxscore.index.name = None

        return boxscore, abbreviated_names

    def get_totals(self):
        """Retrieve the pitching stats totals."""
        pass
