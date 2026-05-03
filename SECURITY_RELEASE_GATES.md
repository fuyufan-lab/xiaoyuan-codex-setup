# Security Release Gates

This public repository can only enforce the public bootstrap boundary. It must not claim that public client code is a complete product security system.

## Public Repository Gate

Required before every push or release:

```bash
bash scripts/publication_guard.sh
```

The guard blocks:

- archived or binary payloads
- backend, runtime, private, or core source paths
- unexpected executable source files
- local machine paths and internal wording
- common credential and key patterns
- MCP tool descriptions that expose internal fields
- local provider inventory that exposes command paths
- manifest hash mismatches
- manifest boundary drift

## Private Release Gate

These items must be handled outside this public repository:

- private client packaging and signing
- server-side authorization and policy gates
- capability routing redaction
- tenant isolation and cross-tenant data checks
- private runtime logs and audit evidence
- abuse, prompt-injection, and unauthorized-dispatch controls
- vulnerability handling and incident response records

Do not publish those implementations, logs, keys, policies, or internal evidence stores here.

## Evidence Gate

Allowed claim from this repository:

- E1: local public-boundary engineering checks pass.

Blocked claims from this repository alone:

- E2: requires at least one real user machine running the full private/client chain.
- E3: requires repeated validation across machines, accounts, networks, and roles.
- E4: requires long-term real usage evidence with correction and incident gates.

External security validation, red-team work, or commercial assurance must be tracked in private evidence systems. A public bootstrap guard is necessary, but it is not proof that the private product is fully resistant to client extraction, manipulation, or abuse.
