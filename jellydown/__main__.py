"""Main entry point for JellyfinDownloader."""

import getpass
import sys
from copy import deepcopy
from urllib.parse import urlparse

import requests

from .api import jget, authenticate
from .classes import Config
from .config import load_config, save_config
from .series import handle_series
from .ui import handle_movies, settings_menu


def validate_jellyfin_server(server_url: str) -> bool:
    url = f"{server_url.rstrip('/')}/System/Info/Public"

    try:
        response = requests.get(url, timeout=5)

        response.raise_for_status()

        data = response.json()

        # Verify expected Jellyfin fields
        required_fields = [
            "ServerName",
            "Version",
            "ProductName",
        ]

        if not all(field in data for field in required_fields):
            return False

        if "Jellyfin" not in data.get("ProductName", ""):
            return False

        return True

    except (
            requests.RequestException,
            ValueError,  # invalid JSON
    ):
        return False


def get_server_url(config: Config) -> str:
    """
    Retrieves and validates the Jellyfin server URL.
    Prompts the user until a reachable server is provided.
    """

    server_url = config.server_url

    while True:
        if not server_url:
            server_url = input(
                "Jellyfin server URL " "(e.g. http://192.168.0.1:8096): "
            ).strip()

            if not server_url.startswith(("http://", "https://")):
                server_url = "http://" + server_url

            parsed_url = urlparse(server_url)

            # Add default port if missing
            if not parsed_url.port:
                add_port = (
                    input("No port specified. " "Add default port 8096? (Y/n): ")
                    .strip()
                    .lower()
                )

                if add_port != "n":
                    server_url = (
                        f"{parsed_url.scheme}://"
                        f"{parsed_url.hostname}:8096"
                        f"{parsed_url.path}"
                    )

        print(f"Checking connection to {server_url}...")

        if validate_jellyfin_server(server_url):
            print("Successfully verified Jellyfin server IP")
            return server_url

        print(
            "Provided server IP is not reachable or does not correspond to a Jellyfin server."
        )

        action = None
        while action not in ("r", "c"):
            action = (
                input("Would you like to " "[r]etry or [c]hange the URL? (r/c): ")
                .strip()
                .lower()
            )
            if action == "c":
                server_url = None
                break
            elif action != "r":
                print("Invalid choice. Please enter r or c.")


def get_api_key_or_token(config: Config, force_token_refresh: bool = False) -> str:
    """
    Attempts to retrieve the API key / token from the config.
    If it's not there, it prompts the user to log in.

    Args:
        config (Config): Configuration object
        force_token_refresh (bool, optional): Force token refresh. Defaults to False.
    Returns:
        str: API key or token
    """
    if not config.api_key or force_token_refresh:
        print("\nAuthentication required.")
        print("1. Login with Username/Password (recommended)")
        print("2. Enter API Key manually")
        print("Note: Username/password is used only once to generate an access token.")
        api_key_or_token = ""
        while not api_key_or_token:
            choice = input("Select [1/2]: ").strip()
            if choice == "1":
                username = input("Username: ").strip()
                password = getpass.getpass("Password: ")
                api_key_or_token = authenticate(config.server_url, username, password)
                if api_key_or_token:
                    print("Login successful.")
                else:
                    print("Login failed, please try again or use API key.")
            elif choice == "2":
                api_key_or_token = input("API key: ").strip()
            else:
                print("Invalid choice. Please enter 1 or 2.")
        return api_key_or_token
    else:
        return config.api_key


def get_user_id_and_name(server_url: str, api_key_or_token: str) -> tuple[str, str]:
    try:
        user_me_details = jget(server_url, "/Users/Me", api_key_or_token)
        user_id = user_me_details.get("Id")
        user_name = user_me_details.get("Name", "(unknown)")
        return user_id, user_name
    except requests.exceptions.HTTPError:
        raise


def determine_user_id_and_name(config: Config) -> tuple[str, str, Config]:
    try:
        user_id, user_name = get_user_id_and_name(config.server_url, config.api_key)
        if not user_id:
            print("Could not determine UserId from /Users/Me")
            sys.exit(1)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401 and config.server_url:
            print(
                "\nAuthentication failed: Invalid or expired API key/token. Trying to get a new one."
            )
            config.api_key = get_api_key_or_token(config, force_token_refresh=True)
            user_id, user_name = get_user_id_and_name(config.server_url, config.api_key)
            return user_name, user_id, config
        raise

    return user_id, user_name, config


def main():
    """Main application entry point."""
    original_config = load_config()
    config = deepcopy(original_config)
    config.server_url = get_server_url(config)
    config.api_key = get_api_key_or_token(config)
    user_id, user_name, config = determine_user_id_and_name(config)

    if config != original_config:
        save_config(config)

    print(f"\nConnected as: {user_name}  UserId: {user_id}")

    while True:
        print("\n--- Main Menu ---")
        print("1. Series")
        print("2. Movies")
        print("3. Settings")
        print("q. Quit")

        choice = input("Select an option: ").strip().lower()

        if choice == "1":
            handle_series(config, user_id)
        elif choice == "2":
            handle_movies(config, user_id)
        elif choice == "3":
            settings_menu(config)
        elif choice == "q":
            sys.exit(0)
        else:
            print("Invalid choice.")


if __name__ == "__main__":
    main()
