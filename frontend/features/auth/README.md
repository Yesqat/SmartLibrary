# frontend/features/auth

PHASE 3 implements Kazakh login/registration forms, shared session provider,
protected layouts, role-based navigation, account summaries and password/session
security controls. The central API client holds access credentials only in memory
and coordinates HttpOnly refresh-cookie operations. Backend authorization remains
authoritative. See docs/AUTHENTICATION.md for the complete contract.
