# Ansible Role: forgejo

![GitHub](https://img.shields.io/github/license/jomrr/ansible-role-forgejo)
![GitHub last commit](https://img.shields.io/github/last-commit/jomrr/ansible-role-forgejo)
![GitHub issues](https://img.shields.io/github/issues-raw/jomrr/ansible-role-forgejo)
[![dev](https://img.shields.io/github/actions/workflow/status/jomrr/ansible-role-forgejo/dev.yml?branch=dev&label=dev)](https://github.com/jomrr/ansible-role-forgejo/actions/workflows/dev.yml?query=branch%3Adev)
[![main](https://img.shields.io/github/actions/workflow/status/jomrr/ansible-role-forgejo/main.yml?branch=main&label=main)](https://github.com/jomrr/ansible-role-forgejo/actions/workflows/main.yml?query=branch%3Amain)

Install Forgejo Linux amd64 releases and manage database configuration, signing
identities and the systemd service.

## Purpose

Install the latest stable Linux amd64 Forgejo release, manage app.ini and enable
and start forgejo.service. Unchanged releases and settings are idempotent.

## Scope

### Managed

- Versioned binaries under /usr/local/libexec/forgejo and the
  /usr/local/bin/forgejo symlink; previous binaries are retained.
- The git system user with a disabled password, /home/git and /bin/bash, and its
  instance SSH signing key.
- Application, repository, LFS and log directories, application settings and
  persistent instance secrets.
- A hardened systemd service with a runtime directory for the optional HTTP Unix
  socket.

### Not Managed

- External databases and users, Redis or Valkey, reverse proxies, SSH daemon
  policy, firewall rules and SELinux policy.
- Application administrators, backups and version compatibility across major
  upgrades.

## Requirements

- Linux amd64 with systemd on a supported distribution.
- For PostgreSQL or MySQL/MariaDB, a prepared database and user with permission
  to create Forgejo tables.
- SQLite uses the downloaded binary and needs no separate database service or
  credentials.
- For external SSH, an SSH daemon accepting public-key authentication for git;
  for HTTP Unix sockets, proxy access to the git group.
- For a Valkey Unix socket, grant git access through forgejo_extra_groups and
  the socket directory permissions.

## Dependencies

```yaml
collections:
  - name: community.general
    version: '>=12.0.0'
  - name: community.crypto
    version: '>=3.0.0'
  - name: containers.podman
    version: '>=1.20.0'
```

## Role Variables

### `forgejo_version`

Type: `str`. Required: `false`.

Stable major.minor.patch release or latest, resolved on each run; old binaries
are retained.

Default:

```yaml
forgejo_version: latest
```

### `forgejo_database_type`

Type: `str`. Required: `false`.

Database backend; mysql supports both MySQL and MariaDB, sqlite3 uses a local
database file.

Default:

```yaml
forgejo_database_type: postgres
```

### `forgejo_database_host`

Type: `str`. Required: `false`.

External database host:port, PostgreSQL socket directory or MySQL socket path;
unused for SQLite.

Default:

```yaml
forgejo_database_host: 127.0.0.1:5432
```

### `forgejo_database_name`

Type: `str`. Required: `false`.

Name of the externally provisioned database; unused for SQLite.

Default:

```yaml
forgejo_database_name: forgejo
```

### `forgejo_database_user`

Type: `str`. Required: `false`.

Login user for the externally provisioned database; unused for SQLite.

Default:

```yaml
forgejo_database_user: forgejo
```

### `forgejo_database_password`

Type: `str`. Required: `false`.

Required for external databases; an empty string supports passwordless
authentication. Unused for SQLite.

### `forgejo_extra_groups`

Type: `list`. Required: `false`.

Additional existing groups for the git account, for example access to a Valkey
socket.

Default:

```yaml
forgejo_extra_groups: []
```

### `forgejo_config_defaults`

Type: `dict`. Required: `false`.

Baseline INI sections recursively merged with forgejo_config; managed paths and
credentials are reserved.

Default:

```yaml
forgejo_config_defaults:
  DEFAULT:
    APP_NAME: Forgejo
    APP_SLOGAN: Beyond coding. We Forge.
    APP_DISPLAY_NAME_FORMAT: '{APP_NAME}'
    RUN_MODE: prod
  database:
    SCHEMA: ''
    SSL_MODE: disable
    LOG_SQL: false
  repository:
    DEFAULT_PRIVATE: public
    DISABLE_STARS: true
  repository.signing:
    SIGNING_NAME: Forgejo instance
    SIGNING_EMAIL: git@localhost
    INITIAL_COMMIT: always
    DEFAULT_TRUST_MODEL: committer
    WIKI: always
    CRUD_ACTIONS: pubkey, twofa, parentsigned
    MERGES: pubkey, twofa, basesigned, commitssigned
  badges:
    ENABLED: true
  server:
    DISABLE_SSH: false
    DOMAIN: localhost
    HTTP_ADDR: 127.0.0.1
    HTTP_PORT: 3000
    LANDING_PAGE: login
    LFS_START_SERVER: true
    OFFLINE_MODE: true
    PROTOCOL: http
    ROOT_URL: http://localhost:3000/
    SSH_DOMAIN: localhost
    SSH_EXPOSE_ANONYMOUS: false
    SSH_PORT: 22
    START_SSH_SERVER: false
    UNIX_SOCKET_PERMISSION: '660'
  mailer:
    ENABLED: false
  service:
    REGISTER_EMAIL_CONFIRM: false
    ENABLE_NOTIFY_MAIL: false
    DISABLE_REGISTRATION: true
    ALLOW_ONLY_EXTERNAL_REGISTRATION: false
    ENABLE_CAPTCHA: false
    REQUIRE_SIGNIN_VIEW: false
    DEFAULT_KEEP_EMAIL_PRIVATE: true
    DEFAULT_ALLOW_CREATE_ORGANIZATION: true
    DEFAULT_ENABLE_TIMETRACKING: true
    NO_REPLY_ADDRESS: noreply.localhost
  picture:
    DISABLE_GRAVATAR: true
    ENABLE_FEDERATED_AVATAR: false
  openid:
    ENABLE_OPENID_SIGNIN: false
    ENABLE_OPENID_SIGNUP: false
  session:
    PROVIDER: file
  log:
    MODE: console
    LEVEL: info
  security:
    PASSWORD_HASH_ALGO: argon2
    REVERSE_PROXY_LIMIT: 1
    REVERSE_PROXY_TRUSTED_PROXIES: 127.0.0.0/8
  ui:
    DEFAULT_THEME: forgejo-auto
    THEMES: forgejo-auto,forgejo-light,forgejo-dark,gitea-auto,gitea-dark,gitea-light
    MEMBERS_PAGING_NUM: 100
    FEED_MAX_COMMIT_NUM: 5
    FEED_PAGING_NUM: 100
    SITEMAP_PAGING_NUM: 100
  webhook:
    ALLOWED_HOST_LIST: external
  actions:
    ENABLED: true
    DEFAULT_ACTIONS_URL: https://code.forgejo.org
  oauth2:
    ENABLED: false
  cron.update_checker:
    ENABLED: false
  repository.pull-request:
    DEFAULT_MERGE_STYLE: merge
  cache:
    ADAPTER: memory
  queue:
    TYPE: level
    MAX_WORKERS: 4
  other:
    SHOW_FOOTER_VERSION: true
    SHOW_FOOTER_TEMPLATE_LOAD_TIME: false
    SHOW_FOOTER_POWERED_BY: false
    ENABLE_SITEMAP: true
    ENABLE_FEED: false
```

### `forgejo_config`

Type: `dict`. Required: `false`.

INI section and key overrides; scalar values only. Managed paths, credentials
and signing identities are reserved.

Default:

```yaml
forgejo_config: {}
```

## Managed Files

- `/usr/local/libexec/forgejo/forgejo-v<version>` Root-owned executable release;
  /usr/local/bin/forgejo selects the configured release.
- `/etc/forgejo/app.ini` Managed template, root:git mode 0640, backed up before
  replacement.
- `/etc/forgejo/secrets/` Persistent instance secrets and, for external
  databases, the database credential; root:git mode 0640 in a 0750 directory.
- `/var/lib/forgejo/data/forgejo.db` SQLite database created and maintained by
  Forgejo when forgejo_database_type is sqlite3.
- `/home/git/.ssh/id_ed25519` Instance signing private key; generated only when
  absent and never rotated by convergence.
- `/etc/systemd/system/forgejo.service` Systemd service; application data lives
  in /var/lib/forgejo and logs in /var/log/forgejo.

## Check Mode

Modules predict changes without installing or rotating secrets. Latest release
resolution performs a read-only API request.

- Check mode is tested after convergence. Before initial installation, missing
  binaries, directories or the service can prevent a complete preview.

## Service Behavior

Binary, identity and configuration changes restart Forgejo. Unit changes reload
systemd first. Every run restores a stopped or disabled service.

## Security Notes

- Secrets are read from existing app.ini values or absolute file: URIs before
  the configuration is replaced; missing values are generated on the managed
  host.
- Keep /etc/forgejo/secrets, existing JWT private keys and the instance SSH
  private key with application backups. Conflicting or unreadable secrets fail
  adoption.
- New installations use HS256 JWT signing; existing active asymmetric JWT keys
  are preserved. Additional application settings may contain secrets and are
  redacted from task output.

## Operational Notes

- forgejo_config recursively overrides forgejo_config_defaults. Keys controlling
  managed paths, the database connection and signing identities are reserved.
- PostgreSQL over TCP remains the default. Select mysql for MySQL/MariaDB or
  sqlite3 for the embedded SQLite database.
- TCP connections use host:port. Unix connections use a PostgreSQL socket
  directory or a MySQL/MariaDB socket file.
- forgejo_database_password is required for external databases, including an
  explicit empty string for passwordless authentication.
- Changing forgejo_database_type selects another backend; existing application
  data is not migrated between databases.
- The HTTP Unix socket is /run/forgejo/forgejo.sock. Its directory is recreated
  by systemd and requires proxy access to the git group.
- MODE=console sends logs to the journal. Set log.MODE to console,file to also
  write to the managed log directory.
- Forgejo has no standalone configuration-validation command. Invalid
  application settings are reported at service startup.
- latest can select a new major release. Check the Forgejo upgrade guide and
  maintain database backups before applying upgrades.

## Supported Platforms

| OS Family | Distribution | Version | Container Image |
| --------- | ------------ | ------- | --------------- |
| RedHat | AlmaLinux | latest | [jomrr/molecule-almalinux:latest](https://hub.docker.com/r/jomrr/molecule-almalinux) |
| Debian | Debian | latest | [jomrr/molecule-debian:latest](https://hub.docker.com/r/jomrr/molecule-debian) |
| RedHat | Fedora | latest | [jomrr/molecule-fedora:latest](https://hub.docker.com/r/jomrr/molecule-fedora) |
| Suse | OpenSuse Leap | latest | [jomrr/molecule-opensuse-leap:latest](https://hub.docker.com/r/jomrr/molecule-opensuse-leap) |
| Suse | OpenSuse Tumbleweed | latest | [jomrr/molecule-opensuse-tumbleweed:latest](https://hub.docker.com/r/jomrr/molecule-opensuse-tumbleweed) |
| Debian | Ubuntu | latest | [jomrr/molecule-ubuntu:latest](https://hub.docker.com/r/jomrr/molecule-ubuntu) |

## Example Playbook

### SQLite

Use the embedded database without external services or database credentials.

```yaml
---
- name: Configure Forgejo with SQLite
  hosts: forgejo
  gather_facts: true
  roles:
    - role: jomrr.forgejo
      forgejo_database_type: sqlite3
```

### PostgreSQL over TCP

Use a prepared database and supply its password from encrypted inventory.

```yaml
---
- name: Configure Forgejo
  hosts: forgejo
  gather_facts: true
  roles:
    - role: jomrr.forgejo
      forgejo_database_host: 127.0.0.1:5432
      forgejo_database_password: "{{ vault_forgejo_database_password }}"
```

### MySQL or MariaDB over TCP

Use a prepared database with the mysql backend and its TCP endpoint.

```yaml
---
- name: Configure Forgejo with MySQL or MariaDB
  hosts: forgejo
  gather_facts: true
  roles:
    - role: jomrr.forgejo
      forgejo_database_type: mysql
      forgejo_database_host: 127.0.0.1:3306
      forgejo_database_password: "{{ vault_forgejo_database_password }}"
```

### PostgreSQL over a Unix socket

Use the socket directory of a local PostgreSQL server.

```yaml
---
- name: Configure Forgejo with local PostgreSQL
  hosts: forgejo
  gather_facts: true
  roles:
    - role: jomrr.forgejo
      forgejo_database_host: /run/postgresql
      forgejo_database_password: "{{ vault_forgejo_database_password }}"
```

### Reverse proxy and Valkey through Unix sockets

Use HTTP and Valkey Unix sockets with a PostgreSQL TCP connection.

```yaml
---
- name: Configure Forgejo behind a reverse proxy
  hosts: forgejo
  gather_facts: true
  roles:
    - role: jomrr.forgejo
      forgejo_database_host: 192.168.100.8:5432
      forgejo_database_password: "{{ vault_forgejo_database_password }}"
      forgejo_extra_groups: [valkey]
      forgejo_config:
        server:
          DOMAIN: git.example.org
          ROOT_URL: https://git.example.org/
          SSH_DOMAIN: git.example.org
          PROTOCOL: http+unix
          HTTP_ADDR: /run/forgejo/forgejo.sock
        repository.signing:
          SIGNING_NAME: git.example.org instance
          SIGNING_EMAIL: git@example.org
        security:
          REVERSE_PROXY_TRUSTED_PROXIES: 127.0.0.0/8,10.0.10.1/32
        webhook:
          ALLOWED_HOST_LIST: external,10.0.0.0/16
        cache:
          ADAPTER: redis
          HOST: redis+socket:///run/valkey/valkey.sock?db=2
```

## References

- [Forgejo configuration](https://forgejo.org/docs/latest/admin/config-cheat-sheet/)
- [Instance signing](https://forgejo.org/docs/latest/admin/advanced/signing/)
- [Upgrade guide](https://forgejo.org/docs/latest/admin/upgrade/)

## Author

[Jonas Mauer](https://github.com/jomrr)

## License

This project is licensed under the MIT License.
See [LICENSE](LICENSE) for the full license text.

Copyright (c) 2026 Jonas Mauer.
