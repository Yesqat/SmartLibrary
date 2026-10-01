# frontend/features/catalog

Implemented public catalog/detail and shared staff book/copy/reference editors.
`api.ts` uses generated schema types and the centralized authenticated client.
TanStack Query keys begin with `catalog`; mutations invalidate related lists,
details and availability. Authorization and state transitions remain backend rules.
