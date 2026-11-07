# Security

For a suspected vulnerability, use GitHub's **Report a vulnerability** option
when private vulnerability reporting is enabled on the repository.
Do not put credentials or agent tokens in public issues.

The panel binds to loopback by default. Operators reach it through SSH
forwarding or an HTTPS reverse proxy. Each agent has a separate hashed token;
rotate it from its server page. Deleting a host revokes its token.

The Linux agent accepts a fixed set of network probes and no arbitrary shell
commands from the panel. It does not require Docker socket access or VPN keys.
A local listening port does not prove external connectivity or a VPN handshake.
