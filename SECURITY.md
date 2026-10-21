# Security policy

The 0.1.x series is an early alpha. Report security issues privately using the
repository's GitHub **Security → Report a vulnerability** feature when available.
If that feature has not yet been enabled, open an issue asking the maintainer for
a private channel without including exploit details, tokens or private files.
No response-time commitment is offered at this stage.

The scanner reads local documents, static manifests, and explicitly supplied
artifacts. It runs only fixed, read-only Git inspection commands, disables Git's
fsmonitor hook, and makes no network requests. It does not run package scripts,
install dependencies, alter Git state, or perform vulnerability scanning.

Symbolic links and Windows reparse points are excluded from document reads.
Markdown scanning is bounded by file count and per-file size. A repository
modified concurrently during a scan may invalidate results; scan a stable
checkout. These precautions are not an operating-system sandbox for hostile
filesystems. Use normal OS isolation when handling untrusted content.

Reports contain project names, relative document paths, version strings and
optional artifact names/hashes. Review those fields before sharing externally.
An integrity hash does not establish the publisher's identity or prove safety.
