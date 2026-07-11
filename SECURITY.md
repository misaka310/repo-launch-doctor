# Security Policy

## Supported versions

The latest version on the default branch is supported.

## Reporting a vulnerability

Use GitHub private vulnerability reporting when it is enabled for the repository. Do not include live credentials, private keys, session cookies, personal data, or private repository contents in a public issue.

Include:

- affected version or commit;
- operating system and Python version;
- minimal reproduction using synthetic data;
- expected and actual behavior;
- whether a report exposed content that should have remained redacted.

## Safety boundaries

Repo Launch Doctor performs static, read-only inspection. It does not execute commands found in the target repository. It may call `git ls-files` to determine whether a risky path is tracked.

The doctor reports suspicious filenames but does not place file contents in generated reports. Users must still review the target repository and its Git history before publishing.
