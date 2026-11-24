# Kvaliteedi agent

Kord nädalas, 45 minutiga, üks juhatuse sõnum. Agent aitab tootmise kvaliteedi andmetest aru saada ja koosolekul selle ühe numbri taga vastata. Ta ei otsi etteantud mustrit. Järgmine nädal võib olla teistsugune.

See on esimene samm. Skript teeb puhastuse, agregaadid ja erindite pingerea. Agent loeb need failid, kontrollib kuni kolm hüpoteesi ja kirjutab sõnumi. Väljund on eesti keeles.

Üks koosolek, üks sõnum. Rahanumber on lisakulu nimetatud baasi vastu, koos arvutuskäiguga. Kogu perioodi praagi summa ei ole sõnum. `Mida juba teeme` ja `Mida juhatuselt vajan` on mustandid. Eurot, mida tekstilehel ei ole, juurde ei mõelda.

## Kasutamine

Projekti juurest. Python on `.venv`.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Analüüs kasutab pandast, openpyxlit ja numpyd. `requests` ja `bs4` on failis, aga seda sammu need ei käivita.

Ava projekt Cursoris.

```text
/create-folder 2026_11_16
```

Perioodi nimes on tähed, numbrid, `_` ja `-`. Tühikut ei ole. Skript teeb `analyses/2026_11_16/` koos kaustadega `input/`, `work/` ja `output/`. Kui kaust on juba olemas, ei kustutata midagi.

Kopeeri Excel kausta `analyses/2026_11_16/input/`. Algfail jääb oma kohale. `input/` all olgu üks tabelifail. Kui neid on mitu, ütle vestluses, milline.

```text
/analyse-data 2026_11_16
```

Kui annad faili tee vestluses kaasa ja seda `input/` all veel ei ole, agent kopeerib selle sinna. Algfaili ei liigutata.

Oota, kuni valmis on:

- `analyses/2026_11_16/output/juhatuse_sonum.md`
- `analyses/2026_11_16/output/vastuste_leht.md`

Kui agent peatub ja ütleb, et register ja kuukokkuvõte ei klapi, sõnumit ei ole. Vahe üle 1% peatab analüüsi.

Sama käiku saab käivitada ka ilma kaldkriipsuta, projekti juurest:

```bash
.venv/bin/python scripts/create_folder.py 2026_11_16
.venv/bin/python scripts/profile.py 2026_11_16
.venv/bin/python scripts/aggregate.py 2026_11_16
.venv/bin/python scripts/outliers.py 2026_11_16
```

`profile.py` järel loeb agent tekstilehe ja kirjutab `work/01_kontekst.md` ning `work/01_hinnad.json`. Hinnad tulevad ainult sellest lehest. Siis tulevad agregaadid ja erindid. Hüpoteesid, sõnum ja vastuste leht kirjutab agent.

Kui `work/03_outlierid.md` on juba olemas ja küsid edasi, analüüsi uuesti ei jooksutata. Vastus tuleb selle kausta tabelitest. Uus lõige läheb `work/kusimused/` alla.

## 45 minutit

| Minutid | Ava | Mida sealt võtad |
| --- | --- | --- |
| 0–10 | `output/juhatuse_sonum.md` | Loe „Mis juhtus“ ja „Mis see maksab“ läbi. Number on failist, seda peast ümber ei arvutata. |
| 10–20 | `work/03_outlierid.md` | Sama lõik, valem, stabiilne suur maht ja uued väärtused. |
| 20–30 | `work/04_hupoteesid.md` | Kuni kolm hüpoteesi. Tagasi lükatud sündmus ei ole põhjus. |
| 30–40 | `output/juhatuse_sonum.md` | Kirjuta kaks mustandit oma sõnadega üle. |
| 40–45 | `output/vastuste_leht.md` | Iga numbri fail ja kuni viis tõenäolist küsimust. |

## Kaust

```text
analyses/2026_11_16/
  input/                  Excel. Seda ei kirjutata üle.
  work/01_kirjeldus.md    lehed, puhastus, kas register ja kuukokkuvõte klapivad
  work/01_kontekst.md     hinnad ja sündmused tekstilehelt
  work/01_hinnad.json     ainult need eurod, mis juhendis on
  work/01_tabelid/        puhastatud csv
  work/02_agregatsioonid/ tükid, määr ja euro lõigete kaupa
  work/03_outlierid.md    pingerida, valem, stabiilne maht
  work/04_hupoteesid.md   kuni kolm hüpoteesi
  work/kusimused/         järelküsimuste tabelid
  output/juhatuse_sonum.md
  output/vastuste_leht.md
```

`/analyse-data` kirjutab `work/` ja `output/` uuesti. `input/` jääb puutumata.

## Sõnum

| Lahter | Mida sinna pannakse |
| --- | --- |
| Mis juhtus | Üks lause. Esimene asi, mille juhatusele ütled. |
| Mis see maksab | Üks number ja valem failist `work/03_outlierid.json`, väli `lisakulu_ymardatud`. |
| Miks see juhtus | Põhjus, mille hüpotees kinnitas. |
| Mida juba teeme | 1–2 mustandit. Sõna MUSTAND on ees. |
| Mida juhatuselt vajan | Üks otsus. Mustand. |

Näidisandmestik on `sample_data/` all. Kood ei sisalda selle faili toodete, tarnijate ega sündmuste nimesid.
