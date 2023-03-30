"""Utility functions for web scraping the MLB The Show game histories."""

import functools
import logging
import time
from typing import Callable

from splinter.driver.webdriver.chrome import WebDriver

# Delay to allow for pages and tables to load.
TIME_DELAY = 2
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


def reload(func):
    """Time delay decorator applied during browser actions involving loading."""

    @functools.wraps(func)
    def wrapper_reload(*args, **kwargs):
        """Reload browser if stop reload condition not met."""
        browser = kwargs["browser"]
        for counter in range(RELOAD_LIMIT + 1):
            is_stop_reload_condition, condition_msg = func(*args, **kwargs)
            time.sleep(TIME_DELAY)
            if is_stop_reload_condition:
                logger_utils.info("Element found, completing browser action.")
                return is_stop_reload_condition, condition_msg
            else:
                if counter == RELOAD_LIMIT:
                    logger_utils.info(
                        f"The maximum number of reload attempts ({RELOAD_LIMIT}) "
                        f"has been reached. The stop reload condition: "
                        f"{condition_msg}, was not met."
                    )
                    return is_stop_reload_condition, condition_msg
                logger_utils.info(
                    f"The loaded page did not meet the stop reload condition: "
                    f"{condition_msg}. Reloading the page. This is reload attempt "
                    f"{counter + 1}."
                )
                browser.reload()

    return wrapper_reload


@reload
def browser_action_with_element_presence_check(
    browser_method: Callable,
    *method_args,
    css_selector: str,
    browser: WebDriver,
    **method_kwargs,
) -> tuple[bool, str]:
    """Perform browser action and check presence of element by css selector."""
    browser_method(*method_args, **method_kwargs)
    is_element_present = browser.is_element_present_by_css(css_selector)
    stop_reload_condition_msg = (
        f"Presence of an element with the css selector '{css_selector}'"
    )
    return is_element_present, stop_reload_condition_msg
