---
name: analyse-data
description: Analüüsib tootmise kvaliteedi andmed etapiti ja koostab juhatuse sõnumi. Kasuta, kui kasutaja kirjutab /analyse-data või küsib olemasoleva analüüsikausta kohta.
disable-model-invocation: true
---

# Analyse data

Python käivitub ainult `.venv/bin/python`. Ära lisa teeke. Ära kirjuta skriptidesse toodete, tarnijate ega sündmuste nimesid.

## Kui kasutaja küsib olemasoleva analüüsi kohta

Kui `analyses/<periood>/work/03_outlierid.md` on olemas ja kasutaja ei palu analüüsi uuesti käivitada, ära jooksuta skripte uuesti. Vasta salvestatud failidest. Uus lõige salvesta `work/kusimused/` alla. Suusõnalist numbrit ära anna.

## Käivitus

1. Kui `analyses/<periood>` puudub, peatu ja ütle, et enne on `/create-folder <periood>`.
2. Kui kasutaja andis faili ja seda `input/` all veel pole, kopeeri see sinna. Algfaili ära liiguta ega kustuta.
3. Kui faili ei antud, jäta `input/` ainsat tabelifaili. Kui faile on mitu, küsi, milline.

```bash
.venv/bin/python scripts/profile.py <periood>
```

Kui väljumiskood on 2, peatu. Ära kirjuta juhatuse sõnumit.

4. Loe `work/01_kirjeldus.md` tekstileht. Kirjuta `work/01_kontekst.md` ja `work/01_hinnad.json`. Iga number tuleb tekstilehelt ja saab välja `allikas`. Ära täida puuduvat numbrit näidisandmetest. Ära pane jsonisse ligikaudset ümbertegemise osakaalu: kulu tuleb registri lipust.

```json
{
  "toote_veerg": "Toode",
  "tukkide_veerg": "Tükke",
  "umber_veerg": "Ümber tehtud",
  "umber_jah": "Jah",
  "umber_ei": "Ei",
  "kliendileiu_veerg": "Avastamise koht",
  "kliendileiu_vaartus": "Kliendi juures",
  "tunnihind": 32,
  "tunnihind_allikas": "rida tekstilehelt",
  "kliendijuhtumi_kulu": 140,
  "kliendijuhtumi_kulu_allikas": "rida tekstilehelt",
  "tooted": {
    "Toote nimi": {
      "omahind": 0,
      "umbertegemise_minutid": 0,
      "allikas": "rida tekstilehelt"
    }
  }
}
```

Veergude nimed võta profiilist, väärtused `Jah` / `Ei` ja kliendileiu väärtus tekstilehe selgitusest.

5. Käivita järjest:

```bash
.venv/bin/python scripts/aggregate.py <periood>
.venv/bin/python scripts/outliers.py <periood>
```

6. Kirjuta kuni kolm hüpoteesi faili `work/04_hupoteesid.md`. Igal hüpoteesil on väide, mida andmed näitaksid kui see peab, mida need näitaksid kui see ei pea, tulemus (kinnitatud, tagasi lükatud või ei otsusta) ja viide tabelile. Uue lõike salvesta `work/kusimused/` csv-na. Konteksti sündmus, mis testis läbi kukub, jääb tagasi lükatuks.

7. Kirjuta `output/juhatuse_sonum.md` ja `output/vastuste_leht.md`.

## Juhatuse sõnum

Üks sõnum. Rahanumber on kinnitatud lõigu `lisakulu_ymardatud` failist `work/03_outlierid.json`. Ära arvuta seda prosa ümber. Valem on sama faili baasi kuu, baasijärgne summa ja kuude arv.

| Lahter | Mida sinna kirjutada |
| --- | --- |
| Mis juhtus | Üks lause. Nii, nagu ütleksid selle juhatusele esimese asjana. |
| Mis see maksab | Üks number + arvutuskäik. |
| Miks see juhtus | Põhjus, mitte sümptom. |
| Mida juba teeme | 1–2 tegevust, mis on sinu enda kontrolli all. |
| Mida juhatuselt vajan | Üks konkreetne otsus, ressurss või mandaat. |

`Mida juba teeme` ja `Mida juhatuselt vajan` on mustandid. Märgi need sõnaga MUSTAND. Kasutaja kirjutab need oma sõnadega üle.

## Vastuste leht

- iga numbri allikas: fail ja filter
- mis väite ümber lükkaks
- kuni viis tõenäolist järelküsimust koos vastuse ja viitega
- tagasi lükatud hüpoteesid ühe reaga
