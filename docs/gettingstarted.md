# Getting Started with Discord-Logger

## Installation
- [Installing Python package](#installing-python-package)
- [Finding Discord User Token](#finding-discord-user-token)
- [Setting up configuration](#setting-up-configuration)

## Usage
- [Logger Deployment](#logger-deployment)

<a name="installing-python-package"></a>
## 1. Installing the Python package dependencies

To install the Python package dependencies you have to type `pip install -r requirements.txt` into the command prompt which already cd into the project directory.


<a name="finding-discord-user-token"></a>
## 2. Finding Discord User Token

You can find your Discord user token through [[Discord Help Guild]](https://discordhelp.net/discord-token).

The user token will make use of [the next part](#setting-up-configuration).

***Notice that please keep your user token as a top-secret in order to prevent others get full access to your account.**

<a name="setting-up-configuration"></a>
## 3. Setting up configuration

You must be done the following steps before using the logger.

1. Make a copy of the `config.example.toml`.
2. Rename the copied file to `config.toml`.
3. Open `config.toml` with any text editor you like.
4. Copy and paste the user bot token to `discord_user_token`.
6. Save the config file.

You can adjust other settings on your own.

<a name="logger-deployment"></a>
## 4. Logger Deployment

1. Run `py main.py` in the command prompt.