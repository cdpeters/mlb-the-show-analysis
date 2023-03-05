"""Utility functions for web scraping the MLB The Show game histories."""

import functools
import logging
import time
from typing import Callable

from selectolax.parser import HTMLParser, Node
from splinter.driver.webdriver.chrome import WebDriver

# Delay to allow for pages and tables to load.
TIME_DELAY = 4
# Reload limit when browser does not display any games and needs to be reloaded.
RELOAD_LIMIT = 2

logger_utils = logging.getLogger(__name__)
logger_utils.setLevel(logging.DEBUG)


def delay(func):
    """Time delay decorator applied during browser actions involving loading."""

    @functools.wraps(func)
    def wrapper_delay(*args, **kwargs):
        """Delay after running `func` function."""
        value = func(*args, **kwargs)
        logger_utils.info("Time delay: START")
        time.sleep(TIME_DELAY)
        logger_utils.info("Time delay: END")
        return value

    return wrapper_delay


# @delay
def browser_action(browser_method: Callable, *args, **kwargs):
    """Pass through function that applies a browser action."""
    return browser_method(*args, **kwargs)


def retrieve_game_nodes(
    parser: HTMLParser, css_selector: str, browser: WebDriver
) -> tuple[list[Node], HTMLParser]:
    """Parse html with additional logic for reloading the browser if needed."""
    for counter in range(RELOAD_LIMIT + 1):
        game_nodes = parser.css(css_selector)
        logger_utils.debug(f"Return type: {type(game_nodes)}")
        logger_utils.debug(f"Length of return value: {len(game_nodes)}")

        if game_nodes:
            return game_nodes, parser
        else:
            if counter == RELOAD_LIMIT:
                logger_utils.info(
                    f"The maxiumum number of reload attempts ({RELOAD_LIMIT}) "
                    f"has been reached. The game history is empty."
                )
                return game_nodes, parser
            logger_utils.info(
                f"Game history did not load. Reloading the page. This is "
                f"reload attempt {counter + 1}."
            )

            browser_action(browser.reload)

            post_reload_html = browser.html
            # Recreate the parser object with the new html.
            parser = HTMLParser(post_reload_html)
