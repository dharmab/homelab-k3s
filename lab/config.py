import pydantic


class Nginx(pydantic.BaseModel):
    base_url: pydantic.AnyHttpUrl


class SteamCmd(pydantic.BaseModel):
    username: str
    password: pydantic.SecretStr


class Arma3(pydantic.BaseModel):
    hostname: str
    admin_password: pydantic.SecretStr
    server_password: pydantic.SecretStr
    server_command_password: pydantic.SecretStr
    steamcmd: SteamCmd


class LabConfig(pydantic.BaseModel):
    nginx: Nginx
    arma3: Arma3
