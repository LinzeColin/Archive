# nab

`nab` is an archived L2 Cloudflare presentation experiment. It was moved from the `LinzeColin/CodexProject` repository root so CodexProject can remain a governance hub instead of a deployment source for this archive surface.

## Public surface

- Worker: `nab`
- Preferred domain: `https://nab.linzezhang.com`
- Static source: `public/index.html`
- Compatibility level: L2 / static-first
- Source SHA256 at migration: `e45c528de97ab2502769160fa9ea2232d701ddb5baf676679512ce877ec6219a`

The static source is the exact byte-for-byte migration of the former CodexProject `nab.html` at task source lock `cfee2cea2f1851cd192406ae70fc0aeef72ed996`.

## Verified deployment

- Deployed source commit: `10129d6c40883941e0845cb15222a46b7b2e3dc9`
- Deployment ID: `2dbbeb7f-92d0-4ad1-8bc1-36a4c1b71004`
- Version ID: `ef260ee4-ca7e-4783-adc9-d9297a77ecb5`
- `https://nab.linzezhang35.workers.dev` and `https://nab.linzezhang.com` both returned HTTP 200 with the `NAB IR Roadshow` title on 2026-07-10.

## Validate and deploy

```bash
shasum -a 256 public/index.html
npx --yes wrangler@4.110.0 deploy --dry-run --config wrangler.jsonc
npx --yes wrangler@4.110.0 deploy --config wrangler.jsonc
```

The deployment command requires local Wrangler OAuth or a correctly scoped Cloudflare token. Credentials must never be stored in this repository.

## Safety boundary

- No database, write path, login, secret, token, cookie, session, or local runtime.
- No dependency on a Worker function; the presentation remains usable as static assets.
- A dry run is not deployment evidence. Record a URL as live only after an HTTP check succeeds.

## Rollback

Use Cloudflare deployment history to restore the previous Worker version, or revert the bounded Archive commit. Do not force-push.
