# Account authorization compatibility — batch 09

This is a server authorization foundation, not the completed private-catalog product.
Existing registrations still use the existing active-user flow; public catalog reads
remain public until the separately reviewed AL-09 access transition. No account is
automatically promoted, migrated or selected as master. Production is not changed by
merging source. Role-management screens and lifecycle endpoints belong to the closing batch.

## Trusted data and decisions

`AccessPolicy` distinguishes active account state, optional `approvalStatus`, existing
role, profile defaults and individual `permissionOverrides`. An absent approval field
preserves legacy `Activo` accounts with roles `admin`/`usuario`; if present, only
`approved` qualifies. Unknown states, roles, permissions or malformed overrides never
grant capabilities. This compatibility mapping is not approval of new pending accounts.

An operator-only `access_policy` entry in the existing excluded `secrets.local.php`
may contain `masterAccountId` and `profilePermissions`. No such file is committed or
changed by this batch. An absent master ID confers master status on nobody; neither
a role flag, registration payload nor being the first administrator selects an owner.
The master record must have the configured stable ID and admin role; it must also be
active to act. Configuring a real identity requires a separate explicit operation.

For configurable capabilities, an individual boolean override prevails over a profile
override; otherwise the established role defaults apply. An absent individual key
means inherit. Master-only capabilities cannot be delegated by these overrides.
`permissions` in a session response contains effective names, not private configuration.
Every protected request refreshes account state and effective permissions from storage;
revoking a capability takes effect even when a session is already open.

## Existing operations

The API checks separate capabilities for catalog creation/update/hiding/review, news,
anime reconciliation and private export. Default administrators retain their previous
operations; users retain proposal creation. Delegating catalog review does not grant
export of profiles, favorites or history. Service callbacks repeat authorization inside
catalog transactions after external metadata I/O, and again when completing a decision.

An external catalog request cannot be approved by its author, including a master.
The server checks the stored author ID before reservation and publication. Direct CRUD
cannot create the same ID while an external proposal remains pending/approving.
Existing manual CRUD and sheet reconciliation are not converted into a new proposal
lifecycle by this batch; comprehensive provenance and review for those paths must be
designed in the closing work. Do not claim universal two-person publication from the
external-request checks alone. Client controls still use the existing role-based layout;
server denials apply independently. Delegated-role UI remains for the closing batch.

## Future governance guards, not deployed lifecycle operations

The policy can distinguish an administrator's pending nomination from a master's
direct approved appointment. An ordinary user cannot nominate administrators even
with a forged capability. It also guards target-specific operations: non-master
administrators cannot delete themselves/other administrators, demote them or change
their credentials; a permitted temporary suspension of another administrator is
distinct from a deletion. The master can restore an administrator. The configured
master identity is protected even if a target record has a stale role.

These methods only return decisions; they do not write appointments, suspend accounts,
notify anyone, schedule expiry, or provide management endpoints. The later suspension
workflow must record a duration, notify master, support reversal and preserve activity.
Permission settings belong exclusively to master, with per-profile/per-account controls.
No configurable permission bypasses protected identity or independent-review rules.
«Resolve conflicts», temporary account duration and suspension expiry remain undefined;
no guessed permissions or timers implement them here. Recovery by the legitimate local
operator is distinct from delegation and must be reviewed before lifecycle deployment.

## Verification and preservation

Synthetic policy, HTTP and transactional tests cover inherited/individual permissions,
forged registration fields, master targeting, nominations, self-review, private export,
and revocation before/after provider resolution. Run `python -m unittest discover -s tests`
with the supported PHP runtime via `PHP_BIN`, or use the isolated full `tools/qa.py` run.
No real provider or production account is needed. AL-12 is explicitly retained as an
unresolved provenance incident; this batch rewrites no IDs, catalog rows or activity.

All future source integrations and production installations follow `CI-CD.md` and
their separate approvals. Do not advance the installed base just because main moved.
