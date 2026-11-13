---
name: create-folder
description: Loob analüüsiperioodi kataloogipuu (input, work, output) kausta analyses alla. Kasuta, kui kasutaja kirjutab /create-folder või palub luua analüüsiperioodi kausta.
disable-model-invocation: true
---

# Create folder

## Sisend

Perioodi nimi kasutaja sõnumist. Lubatud on tähed, numbrid, `_` ja `-`. Näide: `2026_Q2`.

Kui nime ei ole, küsi see enne skripti käivitamist.

## Käivitus

Projekti juurest:

```bash
.venv/bin/python scripts/create_folder.py <periood>
```

Ära loo kaustu käsitsi ja ära kustuta olemasolevat puud.

## Pärast skripti

- Kui skript ütleb, et kataloog on juba olemas, ütle kasutajale, et midagi ei kustutatud.
- Kui puu loodi, ütle kasutajale: kopeeri andmefail kausta `analyses/<periood>/input/` ja käivita `/analyse-data <periood> <fail>`.
- Ära käivita analüüsi ise.
