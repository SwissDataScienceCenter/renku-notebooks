from dataclasses import dataclass, field
from typing import Callable, Optional, Union, List, Dict, Any, Text

from .server_options import _ServerOptionsConfig


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
class _SentryConfig:
    enabled: Union[bool, Text]
    dsn: Optional[Text]
    env: Optional[Text]
    sample_rate: Union[float, Text]

    def __post_init__(self):
        self.enabled = _parse_str_as_bool(self.enabled)
        self.sample_rate = _parse_value_as_numeric(self.sample_rate, float)


@dataclass
class _GitConfig:
    url: Text
    registry: Text


@dataclass
class _SessionImagesConfig:
    default_session: Text
    rpc_server: Text
    git_clone: Text


@dataclass
class _GitProxyConfig:
    port: Union[Text, int] = 8080
    healt_port: Union[Text, int] = 8081
    image: Text = "renku/git-https-proxy:latest"

    def __post_init__(self):
        self.port = _parse_value_as_numeric(self.port, int)
        self.healt_port = _parse_value_as_numeric(self.healt_port, int)


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
    tls_secret: Text
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
    images: _SessionImagesConfig
    git_proxy: _GitProxyConfig
    ingress: _SessionIngress
    ca_certs: _CustomCaCertsConfig
    oidc: _SessionOidcConfig
    storage: _SessionStorageConfig
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
