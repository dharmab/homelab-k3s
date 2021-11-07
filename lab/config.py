"""
Defines the project configuration.

To configure the project, create a JSON file which contains the expected
LabConfig object, such as the following:

{
  "nginx": {
    "base_url": "http://example.com"
  },
  "arma3": {
    "hostname": "Example Arma Server",
    "admin_password": "someadminpassword",
    "server_password": "someserverpassword",
    "server_command_password": "somecommandpassword",
    "steamcmd": {
      "username": "exampleuser",
      "password": "exampleruserspassword"
    }
  }
}

and set the LABCONFIG environment variable to the JSON file's path.
"""
from typing import Any

import pydantic


class ExtendedBaseModel(pydantic.BaseModel):
    def json_with_plaintext_secrets(self, *args, **kwargs) -> str:  # type: ignore
        def plaintext_encoder(obj: Any) -> Any:
            if isinstance(obj, (pydantic.SecretStr, pydantic.SecretBytes)):
                return obj.get_secret_value()
            return pydantic.json.pydantic_encoder

        return self.json(*args, encoder=plaintext_encoder, **kwargs)


class Nginx(ExtendedBaseModel):
    # base_url is the base URL that Nginx will serve path-based ingresses. For
    # example, the Prometheus web UI will be served from base_url +
    # "/prometheus"
    base_url: pydantic.AnyHttpUrl


class SteamCmd(ExtendedBaseModel):
    # username is the username of a Steam user account that will be used to
    # download content from Steam. The Valve Developer Wiki recommends using a
    # separate Steam account with no purchases for this. Steam Guard must be
    # disabled for fully automated installations to function.
    username: str
    # password it he password of the Steam user account.
    password: pydantic.SecretStr


class Arma3(ExtendedBaseModel):
    # hostname is the name of the server displayed in the server browser.
    hostname: str
    # admin_password is the password required for a player to use admin
    # commands.
    admin_password: pydantic.SecretStr
    # server_password is the password required for a player to join the server.
    server_password: pydantic.SecretStr
    # server_command_password is the password required for a player to use
    # server commands:
    server_command_password: pydantic.SecretStr
    # steamcmd is
    steamcmd: SteamCmd


class LabConfig(ExtendedBaseModel):
    # Top level configuration object
    nginx: Nginx
    arma3: Arma3
