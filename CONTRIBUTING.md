# Contributing

Thanks for looking at the kernel. A few ground rules so this stays usable as
a foundation for other builders.

## Scope

The kernel is deliberately minimal. Things that belong in a downstream
application and not here:

- Tradition-specific denominational presets with written framings.
- Brand voice, essays, bios.
- Heavyweight visualizers.
- Payment or donation integrations.
- Deployment and hosting scripts.

Pull requests that add any of the above will be redirected to a fork.

Things that fit here:

- Fixes to the pack format, catalog schema, or reader behaviour.
- Additional public-domain or openly-licensed translation packs, with
  attribution and `license` fields present in the manifest.
- New interface-language chrome packs.
- Accessibility improvements (keyboard, screen reader, high-contrast).
- Offline/PWA improvements that do not raise the install footprint
  materially.

## Developer certificate of origin

By submitting a pull request, you certify that you have the right to submit
the work under Apache-2.0. We follow the [Developer Certificate of Origin
1.1](https://developercertificate.org/). Sign your commits with
`git commit -s`.

## Licensing of contributions

- Code contributions are accepted under Apache License 2.0 (the project
  licence).
- Data contributions carry their own upstream licence, which must be noted in
  the pack's `manifest.json`. Share-alike (CC-BY-SA) data remains share-alike;
  the Apache code licence does not override it.

## Trademarks

See [TRADEMARKS.md](TRADEMARKS.md). The Apache-2.0 licence does not grant
rights to the Concordio or Bible Explorer marks.
