"""ANSI color codes for terminal output."""

# Reset
RESET = "\033[0m"

# Regular colors
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"

# Bright colors
BRIGHT_RED = "\033[91m"
BRIGHT_GREEN = "\033[92m"
BRIGHT_YELLOW = "\033[93m"
BRIGHT_BLUE = "\033[94m"
BRIGHT_MAGENTA = "\033[95m"
BRIGHT_CYAN = "\033[96m"
BRIGHT_WHITE = "\033[97m"

# Bold
BOLD = "\033[1m"
DIM = "\033[2m"

# Background
BG_RED = "\033[41m"
BG_GREEN = "\033[42m"
BG_YELLOW = "\033[43m"
BG_BLUE = "\033[44m"


def red(text: str) -> str:
    return f"{RED}{text}{RESET}"

def green(text: str) -> str:
    return f"{GREEN}{text}{RESET}"

def yellow(text: str) -> str:
    return f"{YELLOW}{text}{RESET}"

def blue(text: str) -> str:
    return f"{BLUE}{text}{RESET}"

def magenta(text: str) -> str:
    return f"{MAGENTA}{text}{RESET}"

def cyan(text: str) -> str:
    return f"{CYAN}{text}{RESET}"

def bright_red(text: str) -> str:
    return f"{BRIGHT_RED}{text}{RESET}"

def bold(text: str) -> str:
    return f"{BOLD}{text}{RESET}"

def dim(text: str) -> str:
    return f"{DIM}{text}{RESET}"


ONTOGENY_LOGO = f"""{BRIGHT_RED}{BOLD}
 #######  ##    ## ########  #######   ######   ######## ##    ## ##    ##
##     ## ###   ##    ##    ##     ## ##    ##  ##       ###   ##  ##  ##
##     ## ####  ##    ##    ##     ## ##        ##       ####  ##   ####
##     ## ## ## ##    ##    ##     ## ##   #### ######   ## ## ##    ##
##     ## ##  ####    ##    ##     ## ##    ##  ##       ##  ####    ##
##     ## ##   ###    ##    ##     ## ##    ##  ##       ##   ###    ##
 #######  ##    ##    ##     #######   ######   ######## ##    ##    ##

{RESET}{BRIGHT_RED}    +--[{('=' * 48)}]--+
{RESET}{BRIGHT_RED}    | {'  >> PROTO-AGI <<  ':^{48}} |
{RESET}{BRIGHT_RED}    +--[{('=' * 48)}]--+
{RESET}"""
