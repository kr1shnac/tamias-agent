# codefix

The one project `policies/acme-codefix.toml` fences the agent to.

- `src/cart.py` - cart totals
- `tests/test_cart.py` - its tests (`python3 -m pytest tests -q`)

Everything outside `company/work/acme/bots/codefix/` is out of bounds for the
`codefix-bot` use case, even though it lives inside the same company area.
