# Licensing

English is authoritative. This repository contains components under different
licenses; it is not offered as an MIT-only firmware project.

## Component licenses

| Component | License | License text / notice |
| --- | --- | --- |
| C5 Rust adapter in the root crate, including its Rust tests and examples | `MIT OR Apache-2.0`, at your option | [LICENSE-MIT](LICENSE-MIT), [LICENSE-APACHE](LICENSE-APACHE), [Cargo.toml](Cargo.toml) |
| C5 native board adapter and native support code in `native/` | `GPL-2.0-or-later` | [COPYING](COPYING) and the SPDX notices in the sources |
| Vendored KWS-X1 source in `upstream/` | Retained upstream licenses and file-specific notices; the reused Rust core is `MIT OR Apache-2.0` | [Upstream MIT license](upstream/LICENSE-MIT), [upstream Apache license](upstream/LICENSE-APACHE) and the relevant crate manifests |
| Third-party dependencies and font data | Their respective licenses and notices | The corresponding dependency distributions; see the font note below |

The C5 native adapter derives from the GPL-2.0-or-later C5 DOOM bring-up.
The linked firmware containing that adapter is distributed subject to the GNU
GPL version 2 or, at your option, a later version, together with the applicable
third-party notices and compatible dependency license choices. The root Rust
crate's permissive license does not replace those combined-work obligations.

When combining `MIT OR Apache-2.0` code with GPLv2 code, the MIT option is
available. Apache-2.0 is compatible with GPLv3, not GPLv2; an Apache-only component
must not be assumed compatible with a GPLv2 distribution. See the
[Apache Software Foundation compatibility explanation](https://www.apache.org/licenses/GPL-compatibility.html).

This summary records the component licensing above. It does not relicense
third-party material or provide a blanket MIT grant for other files. Existing
copyright, attribution, SPDX and license notices must be retained.

## Upstream provenance

The vendored KWS-X1 snapshot is pinned to
`a454c8e6ba5a84747ad6da2928a724e3e714945c` from
[inuchanbt/kws-x1-standalone-rs](https://github.com/inuchanbt/kws-x1-standalone-rs).
[upstream-tree.json](upstream-tree.json) records the original Git blob hashes.
[upstream-patches.json](upstream-patches.json) records the single history-buffer
initialization patch. The upstream renderer/navigation is unchanged. Original
upstream license texts and contributor attribution remain in `upstream/`.

## Dependencies, fonts and vendor images

Cargo dependencies retain their own licenses. In particular, `u8g2-fonts` licenses
its Rust crate as MIT OR Apache-2.0, but the font data has separate terms. Retain
the relevant font attribution and license notices when redistributing font data
or a firmware containing it; the crate's permissive license is not a blanket
license for every font. See the
[u8g2-fonts licensing notice](https://github.com/Finomnis/u8g2-fonts/blob/main/LICENSE)
and [U8g2 license collection](https://github.com/olikraus/u8g2/blob/master/LICENSE).

Owner Flash backups, external settings and vendor bootloader/firmware images
are not distributed by this source repository and are not relicensed here.
The selected owner panel photographs in `docs/images/` are documentation
evidence; this firmware-code licensing summary does not relicense them.

## 日本語の要約

- 新しいC5用RustアダプターとRustテスト・サンプルは、上流に合わせて
  **MIT OR Apache-2.0**です。
- DOOM由来のC5 nativeアダプターとnative補助コードは**GPL-2.0-or-later**です。
  それらをリンクしたファームウェアの配布にはGPLの条件と依存物の条件が適用されます。
- 上流・依存ライブラリー・フォントのライセンスと著作権表示を維持します。
  全体をMITだけに変更したものではありません。
- 所有機バックアップやベンダー製バイナリーは配布・再ライセンスしません。

正本は上記の英語本文および各ライセンス本文です。
