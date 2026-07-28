# FINDINGS.md — the pin ledger (gap ↔ pin, both directions)

Every open gap carries exactly one pin line here; the PIN row reds a gap
without a pin AND a pin without a gap (a pin never disappears by deletion,
only by working the gap off). Pin grammar, one line each:

    - PIN <kind>:<name> — <note>

Kinds: `unmapped:<entity>` (inventoried module not yet consciously mapped),
`reverse_draft:<entity>` (concept doc is a hypothesis, not validated truth),
`to_be:<story-id>` (story landed red, twin still xfail),
`hull_as_is:<contract>` (a foundation contract honestly pinned as failing).

## Open pins

(none — greenfield birth: all entities mapped, all concept docs validated,
K01 landed with a green twin)
