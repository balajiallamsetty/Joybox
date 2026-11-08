# Contrast audit

Measurement uses the rendered page, including text over photos. The guard is `frontend/e2e/contrast_guard.spec.js`. It checks WCAG 2.2 ratios (4.5:1 for normal text, 3:1 for large text and UI borders) at 390px and 1440px, then runs axe `color-contrast`.

| Run | Pairs checked | Failures | Text | Border | Placeholder | Control | Axe color-contrast |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Before | 5193 | 482 | 347 | 102 | 24 | 9 | 25 |
| After | 5128 | 0 | 0 | 0 | 0 | 0 | 0 |

The pair count changed because opaque panels replaced some translucent layers, so fewer text nodes are sampled as sitting on a photo.

## Proof the guard catches light yellow

Axe’s earlier clean result did not flag yellow text. Reintroducing `#ffe175` on white (`Party hours`, class `bg-white text-[#ffe175]`) made the same guard fail:

`CONTRAST yellow-proof pairs=897 failures=4 axe=0`

`WORST 1 1.29:1 #ffe175 on #ffffff / mobile-390 rest text Party hours`

That paragraph was removed after the failure was recorded. The full after run above does not include it.

## Stitch token changes

These two tokens were lightened borders and muted labels. They were darkened only enough to clear 4.5:1 on the light surfaces. Yellow stays a fill.

| Token | File | Before | After | Why |
| --- | --- | --- | --- | --- |
| `outline` | `frontend/tailwind.config.js` | `#7a7583` | `#514a60` | Muted label/border on white was under 4.5:1 |
| `outline-variant` | `frontend/tailwind.config.js` | `#cbc4d3` | `#5c5468` | Translucent lavender borders measured about 1.5:1 |
| `tertiary-fixed` | `frontend/tailwind.config.js` | `#ffe175` | `#ffe175` | Kept as a yellow fill. Text on it is `on-tertiary-fixed` `#221b00` |

## Pairs that changed

| Pair | Before ratio | After treatment | Where |
| --- | ---: | --- | --- |
| `#cbc4d3` on `#ffffff` (52 borders) | under 3:1 | `border-outline` `#514a60` | Footer, booking, contact, admin, landing |
| `#ffe175` / `#eac314` text on white or photos | about 1.3:1 to 1.7:1 | Yellow is a fill; text is `#221b00` or `#715d00` | Promo chips, package badges, policy notes |
| `#ffffff` on photos | 1:1 in the old sampler | Opaque `bg-primary` scrim behind the words | Landing hero, gallery captions |
| `#b40068` on dark purple cards | about 2.1:1 | Icon color `text-secondary-fixed` `#ffd9e4` | Package diamond marks |
| Placeholder `#9ca3af` / `#7a7583` on light fields | under 4.5:1 | Placeholder `#514a60` at full opacity | `frontend/src/styles.css` |
| Disabled controls at `opacity-50` | under 4.5:1 | Solid `bg-surface-container-high` and `text-on-surface-variant` | Booking wizard, booking status, admin login |

## Worst 10 before, and the same regions after

The before ratios of 1:1 were the photo sampler treating covered text as bare pixels. The after shots are the same labels on the opaque scrim or solid button.

| # | Before | After |
| --- | --- | --- |
| 1 | ![Call host before](contrast-audit/before/worst-1-call-host.png) | ![Call host after](contrast-audit/after/worst-1.png) |
| 2 | ![Lock icon before](contrast-audit/before/worst-2-lock-icon.png) | ![Lock icon after](contrast-audit/after/worst-10.png) |
| 3 | 500+ Happy Celebrations, 1:1 on a photo | ![Celebrations after](contrast-audit/after/worst-2.png) |
| 4 | ![Kids special before](contrast-audit/before/worst-4-kids-special.png) | ![Kids special after](contrast-audit/after/worst-3.png) |
| 5 | ![Venue caption before](contrast-audit/before/worst-5-venue-caption.png) | ![Venue caption after](contrast-audit/after/worst-4.png) |
| 6 | ![Teen adult before](contrast-audit/before/worst-6-teen-adult.png) | ![Teen adult after](contrast-audit/after/worst-5.png) |
| 7 | ![LED caption before](contrast-audit/before/worst-7-led-caption.png) | ![LED caption after](contrast-audit/after/worst-6.png) |
| 8 | ![Couples before](contrast-audit/before/worst-8-couples.png) | ![Couples after](contrast-audit/after/worst-7.png) |
| 9 | ![Romantic caption before](contrast-audit/before/worst-9-romantic-caption.png) | ![Romantic caption after](contrast-audit/after/worst-8.png) |
| 10 | ![Squad adda before](contrast-audit/before/worst-10-squad-adda.png) | ![Squad adda after](contrast-audit/after/worst-9.png) |
