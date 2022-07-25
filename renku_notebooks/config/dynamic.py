from dataclasses import dataclass, field
from typing import Callable, Optional, Union, List, Dict, Any, Text


from ..api.schemas.config_server_options import (
    ServerOptionsChoices,
    ServerOptionsDefaults,
)


def _parse_str_as_bool(val: Union[str, bool]) -> bool:
    if type(val) is str:
        return val.lower() == "true"
    elif type(val) is bool:
        return val
    raise ValueError(
        f"Unsupported data type received, expected str or bool, got {type(val)}"
    )


def _parse_value_as_numeric(val: Any, parse_to: Callable) -> Union[float, int]:
    output = parse_to(val)
    if type(output) is not float and type(output) is not int:
        raise ValueError(
            f"parse_to should convert to float or int, it returned type {type(output)}"
        )
    return output


@dataclass
class _ServerOptionsConfig:
    defaults_path: Text
    ui_choices_path: Text

    def __post_init__(self):
        with open(self.defaults_path) as f:
            self.defaults: Dict[
                str, Union[Text, bool, int, float]
            ] = ServerOptionsDefaults().loads(f.read())
        with open(self.ui_choices_path) as f:
            self.ui_choices: Dict[str, Dict[str, Any]] = ServerOptionsChoices().loads(
                f.read()
            )


@dataclass
class _SentryConfig:
    enabled: Union[bool, Text]
    dsn: Optional[Text] = None
    env: Optional[Text] = None
    sample_rate: Union[float, Text] = 0.2

    def __post_init__(self):
        self.enabled = _parse_str_as_bool(self.enabled)
        self.sample_rate = _parse_value_as_numeric(self.sample_rate, float)


@dataclass
class _GitConfig:
    url: Text
    registry: Text


@dataclass
class _GitProxyConfig:
    port: Union[Text, int] = 8080
    health_port: Union[Text, int] = 8081
    image: Text = "renku/git-https-proxy:latest"
    sentry: _SentryConfig = _SentryConfig(enabled=False)

    def __post_init__(self):
        self.port = _parse_value_as_numeric(self.port, int)
        self.health_port = _parse_value_as_numeric(self.health_port, int)


@dataclass
class _GitRpcServerConfig:
    image: Text = "renku/git-rpc-server:latest"
    sentry: _SentryConfig = _SentryConfig(enabled=False)


@dataclass
class _GitCloneConfig:
    image: Text = "renku/git-clone:latest"
    sentry: _SentryConfig = _SentryConfig(enabled=False)


@dataclass
class _SessionStorageConfig:
    pvs_enabled: Union[bool, Text] = True
    pvs_storage_class: Optional[Text] = None
    use_empty_dir_size_limit: Union[Text, bool] = False

    def __post_init__(self):
        self.pvs_enabled = _parse_str_as_bool(self.pvs_enabled)
        self.use_empty_dir_size_limit = _parse_str_as_bool(
            self.use_empty_dir_size_limit
        )


@dataclass
class _SessionOidcConfig:
    client_secret: Text = field(repr=False)
    token_url: Text
    auth_url: Text
    client_id: Text = "renku"
    allow_unverified_email: Union[bool, Text] = False
    config_url: Text = "/auth/realms/Renku/.well-known/openid-configuration"

    def __post_init__(self):
        self.allow_unverified_email = _parse_str_as_bool(self.allow_unverified_email)


@dataclass
class _CustomCaCertsConfig:
    image: Text = "renku/certificates:0.0.2"
    path: Text = "/usr/local/share/ca-certificates"
    secrets: List[Text] = field(default_factory=list)


@dataclass
class _AmaltheaConfig:
    group: Text = "amalthea.dev"
    version: Text = "v1alpha1"
    plural: Text = "jupyterservers"


@dataclass
class _SessionIngress:
    host: Text
    tls_secret: Optional[Text] = None
    annotations: Dict[Text, Text] = field(default_factory=dict)


@dataclass
class _GenericCullingConfig:
    idle_seconds: Union[Text, int] = 86400
    max_age_seconds: Union[Text, int] = 0
    pending_seconds: Union[Text, int] = 0
    failed_seconds: Union[Text, int] = 0

    def __post_init__(self):
        self.idle_seconds = _parse_value_as_numeric(self.idle_seconds, int)
        self.max_age_seconds = _parse_value_as_numeric(self.max_age_seconds, int)
        self.pending_seconds = _parse_value_as_numeric(self.pending_seconds, int)
        self.failed_seconds = _parse_value_as_numeric(self.failed_seconds, int)


@dataclass
class _SessionCullingConfig:
    anonymous: _GenericCullingConfig
    registered: _GenericCullingConfig


@dataclass
class _SessionConfig:
    culling: _SessionCullingConfig
    git_proxy: _GitProxyConfig
    git_rpc_server: _GitRpcServerConfig
    git_clone: _GitCloneConfig
    ingress: _SessionIngress
    ca_certs: _CustomCaCertsConfig
    oidc: _SessionOidcConfig
    storage: _SessionStorageConfig
    default_image: Text = "renku/singleuser:latest"
    enforce_cpu_limits: Union[Text, bool] = False
    autosave_minimum_lfs_file_size_bytes: Union[int, Text] = 1000000
    termination_grace_period_seconds: Union[int, Text] = 600
    image_default_workdir: Text = "/home/jovyan"
    node_selector: Dict[Text, Text] = field(default_factory=dict)
    affinity: Dict[Text, Text] = field(default_factory=dict)
    tolerations: List[Text] = field(default_factory=list)
    container_order_anonymous: List[Text] = field(
        default_factory=lambda x: [
            "jupyter-server",
        ]
    )
    container_order_registered: List[Text] = field(
        default_factory=lambda x: [
            "jupyter-server",
            "oauth2-proxy",
        ]
    )


@dataclass
class _DynamicConfig:
    server_options: _ServerOptionsConfig
    sessions: _SessionConfig
    amalthea: _AmaltheaConfig
    sentry: _SentryConfig
    git: _GitConfig
    s3_mounts_enabled: Union[bool, Text] = False
    anonymous_sessions_enabled: Union[bool, Text] = False
    service_prefix: str = "/notebooks"
    version: str = "0.0.0"

    def __post_init__(self):
        self.s3_mounts_enabled = _parse_str_as_bool(self.s3_mounts_enabled)
        self.anonymous_sessions_enabled = _parse_str_as_bool(
            self.anonymous_sessions_enabled
        )
