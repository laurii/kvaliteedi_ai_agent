# Kasutajajuhend, esmaspäev 16. november 2026

45 minutit enne juhatuse koosolekut. Üks sõnum, üks rahanumber, ja selle numbri taga lahtivõtt, millest saad koosolekul vastata.

Näidisnädal on juba kaustas `analyses/2025_01`. Kui esmaspäeva faili veel ei ole, loe see juhend läbi selle kausta peal. Uus nädal saab uue kausta. Vana kausta sisse uut faili ära pane.

## Esmaspäeva hommik

Mac käivitab iga esmaspäev kell 9 skripti `scripts/monday.py`. See teeb kausta selle esmaspäeva kuupäevaga, näiteks `analyses/2026_11_16`. Analüüsi skript ise ei jooksutata.

Kui Excel on enne kella 9 kaustas `inbox/`, kopeeritakse see `input/` alla. Algfail jääb `inbox/` kausta. Kui `input/` on juba failiga, seda üle ei kirjutata. Kui inboxis on mitu tabelit, ei kopeerita ühtegi.

Kella 9 järel ava Cursor ja kirjuta vestlusesse käsk, mille skript ette ütleb:

```text
/analyse-data 2026_11_16
```

Sama skripti saad käivitada ka ise:

```bash
.venv/bin/python scripts/monday.py
```

Kui andsid faili tee vestluses kaasa ja seda `input/` all veel ei ole, agent kopeerib selle sinna.

Oota, kuni valmis on kaks faili:

- `analyses/2026_11_16/output/juhatuse_sonum.md`
- `analyses/2026_11_16/output/vastuste_leht.md`

Kui agent peatub ja ütleb, et register ja kuukokkuvõte ei klapi, sõnumit ei ole. Ära lähe koosolekule selle nädala numbri otsa. Paranda fail või küsi, milline leht on register.

## 45 minutit

Ava failid selles järjekorras. Number, mille ütled, on sõnumi number. Ära arvuta seda peast ümber.

| Minutid | Ava | Mida sa sealt võtad |
| --- | --- | --- |
| 0–5 | `output/juhatuse_sonum.md` | Loe „Mis juhtus“ ja „Mis see maksab“ kõva häälega läbi. |
| 5–10 | `work/03_outlierid.md` | Leia sama lõik. Valem on baasijärgne summa miinus baasi kuu korda baasijärgsete kuude arv. |
| 10–20 | `work/05_koosolek/index.md` | Ülekulu osad, maht või määr, kallim kuu ja suurim hüpe, mis ei muutunud, liinil püütud kliendileid, kas leid jääb teise baasiga samaks. |
| 20–25 | `output/joonis.svg` | Määr kuude lõikes ja ülekulu toodete lõikes. Märgid kuude all on juhendi sündmused. See on visand. |
| 25–35 | `output/juhatuse_sonum.md` | Kirjuta „Mida juba teeme“ ja „Mida juhatuselt vajan“ oma sõnadega üle. Need on mustandid, sõna MUSTAND on ees. |
| 35–45 | `output/vastuste_leht.md` | Viis tõenäolist küsimust. Iga numbri taga on fail. |

`work/05_koosolek/` tabelid, kui keegi küsib täpsemalt:

| Fail | Mida see vastab |
| --- | --- |
| `ulekulu_osad.csv` | Kui palju on mahakandmine, ümbertegemine ja kliendileid. |
| `maht_vs_maar.csv` | Kas kulu kasvas suuremast toodangust, kõrgemast määrast või sellest, et defektne tükk maksab teisiti. |
| `kuud.csv` | Iga kuu tükid, määr ja eurod. |
| `kuude_vordlus.csv` | Kõige kallim kuu ja suurima hüppe kuu. Kui need erinevad, ütle mõlemad. |
| `muutumatu.csv` | Mis fookustootel jäi paigale. Üks tõusev defekt ei tähenda, et kvaliteet kukkus üleni. |
| `kliendileid_liinil.csv` | Mis ülekulu oleks, kui sama defekt oleks jäänud liinile. Eeldus on samas failis. |
| `baas.csv` | Sama leid esimese kuu, kahe kuu ja kolme kuu baasil. |

## Koosolekul

Küsi samas vestluses ja nimeta kaust, näiteks `2026_11_16`. Agent ei käivita analüüsi uuesti. Vastus tuleb selle kausta tabelitest. Uus lõige salvestatakse `work/kusimused/` alla ja küsimus jääb faili `work/kusimused/kusimused.md`.

Kui küsid hinda, mida Excelis ei ole, ütle see hind ise. Agent ei täida puuduvat eurot näidisandmetest.

Üks sõnum jääb üheks sõnumiks. Soodustus, teine baas ja liinil püütud kliendileid on vastuste lehel, mitte teine pealkiri, kuni sa ise palud sõnumit muuta.

## Mida kaustas on

```text
analyses/2026_11_16/
  input/                 Excel. Seda ei kirjutata üle.
  work/01_kirjeldus.md   lehed, puhastus, kas register ja kuukokkuvõte klapivad
  work/01_kontekst.md    hinnad ja sündmused tekstilehelt
  work/03_outlierid.md   pingerida, valem, stabiilne maht, uued väärtused
  work/04_hupoteesid.md  kuni kolm hüpoteesi ja kas need pidasid
  work/05_koosolek/      lahtivõtt
  work/kusimused/        järelküsimused
  output/juhatuse_sonum.md
  output/vastuste_leht.md
  output/joonis.svg
```

## Enne kui lähed sisse

- Sõnumis on üks rahaarv ja arvutuskäik.
- Mustandid on sinu sõnadega üle kirjutatud.
- Sa oskad öelda, milline kuu on kallim ja millises kuus oli hüpe.
- Sa oskad nimetada ühe defekti, mis ei liikunud.
- Visand on lahti, et saaksid selle kümne minuti sisse panna.
