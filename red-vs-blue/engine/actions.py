"""Action definitions for Red (attacker) and Blue (defender).

Kept as plain enums + metadata so they serialize cleanly to MongoDB and render
directly in the UI log with the plain-English text from the design brief.
"""
from __future__ import annotations

from enum import Enum


class RedAction(str, Enum):
    PHISHING = "phishing"                 # usual way in at the network edge
    PASSWORD_GUESS = "password_guess"     # try common passwords
    EXPLOIT = "exploit"                   # use a known flaw in un-patched software
    STEAL_PASSWORDS = "steal_passwords"   # grab saved logins on a held node
    MOVE_SIDEWAYS = "move_sideways"       # hop to a connected node
    STEAL_DATA = "steal_data"             # copy files off a node (crown jewel = win)


class BlueAction(str, Enum):
    SCAN = "scan"                 # look for signs of Red; reveals hidden attacks
    PATCH = "patch"               # update software so exploits stop working
    RESET_PASSWORDS = "reset"     # make stolen passwords useless
    FIREWALL = "firewall"         # block a line so Red can't travel it
    ISOLATE = "isolate"           # unplug a device; stops spread but it's offline
    RESTORE = "restore"           # wipe a taken node, give it back to Blue


# Plain-English templates for the UI log (design brief wants human-readable lines).
RED_TEXT = {
    RedAction.PHISHING: "sent a phishing email to {target}",
    RedAction.PASSWORD_GUESS: "guessed passwords on {target}",
    RedAction.EXPLOIT: "exploited old software on {target}",
    RedAction.STEAL_PASSWORDS: "stole admin password on {target}",
    RedAction.MOVE_SIDEWAYS: "moved {source} -> {target}",
    RedAction.STEAL_DATA: "stole data from {target}",
}

BLUE_TEXT = {
    BlueAction.SCAN: "scanned {target}",
    BlueAction.PATCH: "patched {target}",
    BlueAction.RESET_PASSWORDS: "reset passwords on {target}",
    BlueAction.FIREWALL: "added a firewall rule at {target}",
    BlueAction.ISOLATE: "isolated {target}",
    BlueAction.RESTORE: "restored {target} from backup",
}

RED_ACTIONS = list(RedAction)
BLUE_ACTIONS = list(BlueAction)
