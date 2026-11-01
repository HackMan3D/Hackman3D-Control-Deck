# HCD Base Slim bill of materials

This list covers the purchased parts required to build one HCD Base Slim. The
3D-printed enclosure, diffuser and keycaps are supplied separately with the
model files.

> **Important:** use the exact option shown in the **Option to select** column.
> Marketplace listings often group several incompatible variants on the same
> page.

## Electronics

| Quantity | Component | Exact specification | Option to select | AliExpress | Amazon |
| ---: | --- | --- | --- | --- | --- |
| 1 | ESP32-C3 Super Mini | USB-C version, supplied with solderable header pins | **ESP32-C3 Super Mini, USB-C, with pins** | [Affiliate link](https://s.click.aliexpress.com/e/_c2xGStWx) | [ESP32-C3 Super Mini](https://link.amazon/B0c0GSeeM) |
| 9 | Low-profile switches | Low-profile mechanical keyboard switches compatible with the supplied keycaps | **Low-profile switch** — do not select a standard-height MX switch | [Affiliate link](https://s.click.aliexpress.com/e/_c4KR3RQF) | [Low-profile switches](https://link.amazon/B0eGV0Wzt) |
| 1 | Red connection LED | 5 mm through-hole LED, approximately 2–2.2 V | **Red, 5 mm** | [Affiliate link](https://s.click.aliexpress.com/e/_c3YHBgMF) | [OWOFYDR, pack of 100](https://link.amazon/B05HMu4Cu) |
| 2 | Red LED resistors | 100 ohm, 1/4 W, wired in series for 200 ohm total | **100R** | [Affiliate link](https://s.click.aliexpress.com/e/_c4OATELh) | [BOJACK resistor assortment](https://link.amazon/B0byWhsql) |
| 50 cm | White LED strip | 5 V, 3 mm wide, two wires, white light | **5 V · 3 mm · 2 wires · white · 0.5 m** | [Affiliate link](https://s.click.aliexpress.com/e/_c2RHDkfD) | [5 V narrow LED strip](https://link.amazon/B03S62oht) |
| 1 | N-channel MOSFET | IRLB8721 / IRLB8721PBF, TO-220 package | **IRLB8721** | [Affiliate link](https://s.click.aliexpress.com/e/_c3tLt3CX) | [IRLB8721PBF, pack of 5](https://link.amazon/B074mJqXJ) |
| 1 | MOSFET gate resistor | 100 ohm, 1/4 W | **100R** | [Affiliate link](https://s.click.aliexpress.com/e/_c4OATELh) | [BOJACK resistor assortment](https://link.amazon/B0byWhsql) |
| 1 | USB-C cable | Must support both data and power | **Data + charging cable** — not a charge-only cable | [Affiliate link](https://s.click.aliexpress.com/e/_c4qXiokb) | [ZeroneTeck USB-C data cable](https://link.amazon/B075uRWBR) |

## Wiring and hardware

| Quantity | Component | Exact specification | Option to select | AliExpress | Amazon |
| ---: | --- | --- | --- | --- | --- |
| As required | Female Dupont leads | 2.54 mm jumper wires; connector retained only at the ESP32 end | **Female-to-female** | [Affiliate link](https://s.click.aliexpress.com/e/_c40SPRKx) | [Female-to-female Dupont wires](https://link.amazon/B0e1pGaxf) |
| As required | Heat-shrink tubing | Small diameter, sized to insulate each bare Dupont contact separately | **Small-diameter heat-shrink tubing** | [Affiliate link](https://s.click.aliexpress.com/e/_c3riUoer) | [HUAKAYO heat-shrink assortment](https://link.amazon/B06use4Lj) |
| 6 | Screws | M2 × 10 mm, countersunk / flat head | **M2 · 10 mm · countersunk head** | [Affiliate link](https://s.click.aliexpress.com/e/_c3LS3Kv9) | [WZHUIDA M2 assortment](https://link.amazon/B04AuJdUT) |

## Assembly details

- Daisy-chain one contact of every switch to create a shared ground bus.
- Keep the female Dupont contact only at the ESP32 end. Remove its plastic
  housing and insulate the individual metal contact with heat-shrink tubing.
- Cut, strip and solder the other end of each wire directly to its component.
- Solder the ESP32 header pins and bend them to 90 degrees to reduce the height.
- Wire the two 100 ohm red-LED resistors in series, for 200 ohm total.
- Drive the 5 V LED strip through the IRLB8721 MOSFET and its 100 ohm gate
  resistor. Do not power the strip directly from a GPIO.

## Included printable files

- upper enclosure;
- lower enclosure;
- LED diffuser, to print in white or translucent material;
- low-profile keycap, to print nine times.

## Affiliate disclosure

Some AliExpress and Amazon links above are affiliate links. Using them supports
continued HackMan3D development without changing the buyer's price.
