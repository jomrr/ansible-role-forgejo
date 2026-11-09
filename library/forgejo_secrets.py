#!/usr/bin/python
"""Preserve Forgejo installation secrets before replacing app.ini."""

import configparser
import os
from pathlib import Path
import re
import tempfile

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = r"""
module: forgejo_secrets
short_description: Preserve or initialize Forgejo instance secrets
description:
  - Copies existing inline or file-referenced secrets into protected files.
  - Generates missing secrets with the installed Forgejo binary.
  - Preserves existing asymmetric JWT signing keys and rejects missing keys.
  - New installations use HS256 JWT signing with independent random secrets.
options:
  config_path:
    description: Existing application configuration to read before templating.
    type: path
    required: true
  directory:
    description: Existing directory for persistent secret files.
    type: path
    required: true
  binary:
    description: Absolute path to the installed Forgejo executable.
    type: path
    required: true
extends_documentation_fragment:
  - ansible.builtin.files
author:
  - Jonas Mauer
"""

EXAMPLES = r"""
- name: Preserve or initialize instance secrets
  forgejo_secrets:
    config_path: /etc/forgejo/app.ini
    directory: /etc/forgejo/secrets
    binary: /usr/local/bin/forgejo
    owner: root
    group: git
    mode: '0640'
  no_log: true
"""

RETURN = r"""
config:
  description: INI sections containing file references and JWT signing settings.
  returned: success
  type: dict
"""


def ini_value(value: str) -> str:
    """Unquote scalar secrets without interpreting interpolation as credentials."""
    value = value.strip()
    for quote in ('"""', '"', "`"):
        if value.startswith(quote):
            end = value.find(quote, len(quote))
            suffix = value[end + len(quote) :].strip()
            if end < 0 or (suffix and not suffix.startswith((";", "#"))):
                raise ValueError("Unterminated or ambiguous quoted configuration value")
            value = value[len(quote) : end]
            break
    else:
        value = re.split(r"\s+[;#]", value, maxsplit=1)[0].strip()
    if "\n" in value or "\r" in value or "%(" in value:
        raise ValueError("Multiline or interpolated secrets require a file URI")
    return value


class ForgejoConfig(configparser.ConfigParser):
    """Keep Forgejo option names case-sensitive."""

    def optionxform(self, optionstr: str) -> str:
        return optionstr


def read_config(path: Path) -> configparser.ConfigParser:
    """Read Forgejo's unnamed root and repeated sections without interpolation."""
    parser = ForgejoConfig(interpolation=None, strict=False, delimiters=("=",))
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return parser
    parser.read_string("[DEFAULT]\n" + content)
    return parser


def config_value(
    config: configparser.ConfigParser, section: str, key: str, fallback: str = ""
) -> str:
    """Read one optional scalar from the previous configuration."""
    return ini_value(config.get(section, key, fallback=fallback))


def read_secret(path: Path) -> str:
    """Reject empty persisted secrets instead of silently rotating them."""
    value = path.read_text(encoding="utf-8").strip()
    if not value:
        raise ValueError(f"Empty secret file: {path}")
    return value


def existing_secret(config: configparser.ConfigParser, section: str, key: str) -> str:
    """Resolve the supported file URI or inline value from the old configuration."""
    inline = config_value(config, section, key)
    uri = config_value(config, section, key + "_URI")
    if uri and inline:
        raise ValueError(f"Both {section}.{key} and its URI are configured")
    if uri:
        if not uri.startswith("file:/"):
            raise ValueError(f"{section}.{key}_URI must be an absolute file URI")
        return read_secret(Path(uri.removeprefix("file:")))
    return inline


def jwt_settings(
    config: configparser.ConfigParser, section: str, prefix: str, installed: bool
) -> dict[str, str]:
    """Keep asymmetric signing identities when adopting an existing installation."""
    enabled = config_value(config, section, "ENABLED", "true").lower() == "true"
    default = "RS256" if installed and section == "oauth2" and enabled else "HS256"
    algorithm = config_value(config, section, prefix + "SIGNING_ALGORITHM", default)
    result = {prefix + "SIGNING_ALGORITHM": algorithm}
    if algorithm.startswith("HS"):
        return result
    default_path = "jwt/private.pem" if section == "oauth2" else "lfs/private.pem"
    key_path = Path(
        config_value(config, section, prefix + "SIGNING_PRIVATE_KEY_FILE", default_path)
    )
    if not key_path.is_absolute():
        work = Path(config_value(config, "DEFAULT", "WORK_PATH", "/var/lib/forgejo"))
        data = Path(config_value(config, "server", "APP_DATA_PATH", str(work / "data")))
        if not data.is_absolute():
            data = work / data
        key_path = data / key_path
    if not key_path.is_file():
        raise ValueError(
            f"Existing JWT signing key is missing: {key_path}; "
            "restore it before adopting this installation"
        )
    result[prefix + "SIGNING_PRIVATE_KEY_FILE"] = str(key_path)
    return result


def persist_secret(
    module: AnsibleModule, path: Path, previous: str, generator: str
) -> bool:
    """Create one secret atomically and converge its file permissions."""
    try:
        current = read_secret(path)
    except FileNotFoundError:
        current = ""
    if current and previous and current != previous:
        raise ValueError(f"Persisted secret conflicts with app.ini: {path.name}")
    changed = not current
    if changed and not module.check_mode:
        if not previous:
            return_code, previous, _stderr = module.run_command(
                [module.params["binary"], "generate", "secret", generator]
            )
            if return_code or not previous.strip():
                raise ValueError(f"Forgejo could not generate {generator}")
        descriptor, temporary = tempfile.mkstemp(dir=module.tmpdir)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(previous.strip())
        module.atomic_move(temporary, str(path))
    if current or not module.check_mode:
        arguments = module.load_file_common_arguments(module.params, path=str(path))
        changed = module.set_fs_attributes_if_different(arguments, changed)
    return changed


def configure(module: AnsibleModule) -> tuple[bool, dict[str, dict[str, str]]]:
    """Read all signing identities before creating files or changing configuration."""
    config_path = Path(module.params["config_path"])
    config = read_config(config_path)
    result = {
        "oauth2": jwt_settings(config, "oauth2", "JWT_", config_path.exists()),
        "server": jwt_settings(config, "server", "LFS_JWT_", config_path.exists()),
        "security": {},
    }
    secrets = (
        ("security", "SECRET_KEY", "secret_key", "SECRET_KEY"),
        ("security", "INTERNAL_TOKEN", "internal_token", "INTERNAL_TOKEN"),
        ("server", "LFS_JWT_SECRET", "lfs_jwt_secret", "JWT_SECRET"),
        ("oauth2", "JWT_SECRET", "oauth2_jwt_secret", "JWT_SECRET"),
    )
    previous = [existing_secret(config, section, key) for section, key, _, _ in secrets]
    changed = False
    for (section, key, filename, generator), value in zip(secrets, previous):
        path = Path(module.params["directory"]) / filename
        changed = persist_secret(module, path, value, generator) or changed
        result[section][key + "_URI"] = "file:" + str(path)
    return changed, result


def main() -> None:
    """Run the module without exposing credentials in results or errors."""
    module = AnsibleModule(
        argument_spec={
            "config_path": {"type": "path", "required": True},
            "directory": {"type": "path", "required": True},
            "binary": {"type": "path", "required": True},
        },
        add_file_common_args=True,
        supports_check_mode=True,
    )
    try:
        changed, config = configure(module)
    except configparser.Error:
        module.fail_json(
            msg="Cannot parse the existing app.ini; no credentials were replaced"
        )
        return
    except (OSError, ValueError) as error:
        module.fail_json(msg=str(error))
        return
    module.exit_json(changed=changed, config=config)


if __name__ == "__main__":
    main()
