"""Relevant classes for web scraping game histories."""

from dataclasses import InitVar, dataclass, field


@dataclass
class Gamer:
    """Gamer class containing gamer id information."""

    _name: str
    _gamer_tag: str
    _url_gamer: str = field(init=False)
    url_base: InitVar[str] = "https://mlb22.theshow.com/universal_profiles"
    url_infix: InitVar[str] = "game_history?page="
    url_suffix: InitVar[str] = "&mode=ARENA&subdomain=mlb22"

    def __post_init__(self, url_base, url_infix, url_suffix) -> None:
        """Build the url."""
        self._url_gamer = f"{url_base}/{self._gamer_tag}/{url_infix}1{url_suffix}"

    def __str__(self) -> str:
        """Provide pretty response for Gamer instance."""
        return (
            f"     Name: {self._name}\n"
            f"Gamer Tag: {self._gamer_tag}\n"
            f"Gamer URL: {self._url_gamer}"
        )

    @property
    def name(self) -> str:
        """Read _name."""
        return self._name

    @property
    def gamer_tag(self) -> str:
        """Read _gamer_tag."""
        return self._gamer_tag

    @property
    def url_gamer(self) -> str:
        """Read _url_gamer."""
        return self._url_gamer
