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
import enum
import string
from typing import Any, List

import pydantic


class ExtendedBaseModel(pydantic.BaseModel):
    def json_with_plaintext_secrets(self, *args, **kwargs) -> str:  # type: ignore
        def plaintext_encoder(obj: Any) -> Any:
            if isinstance(obj, (pydantic.SecretStr, pydantic.SecretBytes)):
                return obj.get_secret_value()
            return pydantic.json.pydantic_encoder  # pylint: disable=no-member

        return self.json(*args, encoder=plaintext_encoder, **kwargs)


class Issuer(str, enum.Enum):
    SELF_SIGNED = "selfsigned"
    LETS_ENCRYPT_STAGING = "letsencrypt-staging"
    LETS_ENCRYPT = "letsencrypt"


class CertManager(ExtendedBaseModel):
    # email is an email address for Let's Encrypt to contact in case of issues
    email: pydantic.EmailStr
    # cloudflare_api_token is an API token with permission to edit the DNS
    # zone required by the ACME DNS01 solver.
    cloudflare_api_token: pydantic.SecretStr
    # issuer is the issuer to use. You should use the self-signed issuer for
    # a localhost cluster. Use the Let's Encrypt staging issuer to verify your
    # configuration before switching to the production issuer.
    issuer: Issuer = Issuer.SELF_SIGNED


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
    # password is the password of the Steam user account.
    password: pydantic.SecretStr


class Arma3Mod(ExtendedBaseModel):
    # name is a snake_case name for the mod.
    name: str
    # workshop_id is the mod's workshop ID.
    workshop_id: int

    @classmethod
    @pydantic.validator("name")
    def name_must_be_snake_case(cls, v: str) -> str:
        valid_characters = string.ascii_lowercase + string.digits + "_."
        if not all(c in valid_characters for c in v):
            raise ValueError("name must be snake_case")
        return v

    @classmethod
    @pydantic.validator("workshop_id")
    def workshop_id_must_be_postive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("workshop_id must be a positive integer")
        return v


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
    # steamcmd is credentials to authenticate to Steam.
    # Note that Arma 3 does not need to be purchased to download the dedicated
    # server, but DOES need to be purchased to download mods.
    steamcmd: SteamCmd
    # mods is a set of mods to install on the server.
    mods: List[Arma3Mod] = []

    @classmethod
    @pydantic.validator("mods")
    def mods_must_be_unique(cls, v: List[Arma3Mod]) -> List[Arma3Mod]:
        names = []
        ids = []
        for mod in v:
            if mod.name in names:
                raise ValueError("Mod with name {mod.name} is non-unique")
            names.append(mod.name)

            if mod.workshop_id in ids:
                raise ValueError("Mod with ID {mod.workshop_id} is non-unique")
            ids.append(mod.workshop_id)

        return v


class LabConfig(ExtendedBaseModel):
    # Top level configuration object
    cert_manager: CertManager
    nginx: Nginx
    arma3: Arma3
