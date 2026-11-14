# Näidisagendi koostamine

See agent valmistab ühe juhatuse sõnumi. Ta ei otsi etteantud mustrit. Skript teeb iga nädal sama arvutuse. Agent loeb tulemuse ja kirjutab sõnad.

Üks etapp lõpeb failiga. Järgmine etapp loeb seda faili. Kui etapp peatub, sõnumit ei kirjutata.

Käsk on `/analyse-data <periood>`. Python on `.venv/bin/python`. Uusi teeke ei lisata.

## Etapp 1. Kaust

Eesmärk on anda nädalale oma koht, enne kui andmeid puututakse.

Kasutaja ütleb `/create-folder <periood>`. Skript on `scripts/create_folder.py`. Nimes on tähed, numbrid, `_` ja `-`.

Tekib `analyses/<periood>/` koos `input/`, `work/` ja `output/` kaustadega. Kui puu on juba olemas, ei kustutata midagi.

Kasutaja kopeerib Exceli kausta `input/`. Algfail jääb oma kohale.

Järgmine etapp ei alga, kui seda puud ei ole.

## Etapp 2. Kirjeldus

Eesmärk on aru saada, mis lehed failis on, ja kas numbrid klapivad.

Skript on `scripts/profile.py`. Ta eraldab faktilehed tekstilehest. Register on leht, millel on tunnus ja kuupäev. Kuukokkuvõte on teine faktileht.

Puhastus: rida, millel tunnus ja kuupäev on mõlemad tühjad, ei ole juhtum. Välja jäetud ridade ja tükkide arv läheb kirjeldusse.

Pärast puhastust võrreldakse registri tükke kuukokkuvõtte praagi tükkidega, kuu ja toote lõikes. Kui suhteline vahe on üle 1%, skript lõpetab koodiga 2.

Väljund:

- `work/01_kirjeldus.md`
- `work/01_profiil.json`
- `work/01_tabelid/` puhastatud csv

Kui klappimine ebaõnnestub, etapid 3–10 jäävad tegemata.

## Etapp 3. Kontekst ja hinnad

Eesmärk on võtta raha ja sündmused tekstilehelt, mitte näidisandmetest.

Selle etapi teeb agent, mitte skript. Allikas on `work/01_kirjeldus.md` tekstileht.

Väljund:

- `work/01_kontekst.md` — tooted, hinnad, mis perioodil toimus
- `work/01_hinnad.json` — omahind, ümbertegemise minutid, tunnihind, kliendijuhtumi kulu, igaühel rida `allikas`

Ümbertegemise osakaalu ligikaudset protsenti jsonisse ei panda. Kulu tuleb registri lipust. Puuduvat eurot ei täideta.

## Etapp 4. Agregatsioonid

Eesmärk on panna samad mõõdud igale nädalale, et lõike saaks võrrelda.

Skript on `scripts/aggregate.py`. Ta loeb puhastatud tabelid ja `work/01_hinnad.json`, kui see on olemas.

Iga lõige on periood ja toode, ning periood, toode ja üks kategooria. Kategooriad tulevad andmetest. Nimesid skript ei tunne.

Igas failis on tükid, juhtumid, toodetud kogus ja määr. Määr on tükid jagatud toodanguga.

Euro, kui hinnad on olemas:

- mahakandmine on tükid, mida ei tehtud ümber, korrutatud omahinnaga
- ümbertegemine on ümber tehtud tükid korrutatud minutite, tunnihinna ja 1/60-ga
- kliendileid on juhtumite arv, mitte tükid, korrutatud juhtumi kuluga

Väljund on `work/02_agregatsioonid/`. `index.md` ütleb, mida iga fail näitab.

## Etapp 5. Erindid

Eesmärk on eraldada tõus suurest stabiilsest mahust.

Skript on `scripts/outliers.py`. Baas on ajatelje esimene kolmandik, aga vähemalt kaks esimest perioodi, kui perioode on vähemalt neli. Baas kirjutatakse väljundisse.

Lõik tõuseb esile, kui määr kasvab vähemalt 0,5 protsendipunkti ja tükkide või eurode muutus on suur. Suur tähendab viie esimese seas või vähemalt viiendik toote tõusust.

Eurode ja tükkide pingerida on eraldi. Suur tükimaht ei ole sama mis kallis leid.

Kolm hunnikut:

- pingerida — määr tõusis ja muutus on suur
- stabiilsed — palju tükke, määr ei liikunud, sõnumisse ei lähe
- uued väärtused — baasis tükke ei olnud, iseenesest ei ole põhjus

Lisakulu on baasijärgne summa miinus baasi keskmine kuu korda baasijärgsete kuude arv. Sõnumi number on kinnitatud lõigu `lisakulu_ymardatud`. Seda ei arvutata prosa ümber.

Väljund on `work/03_outlierid.md` ja `work/03_outlierid.json`.

## Etapp 6. Sündmused

Eesmärk on panna juhendi sündmused joonisele siltidena, mitte põhjustena.

Selle etapi teeb agent tekstilehe järgi. Väljund on `work/01_sundmused.json`. Iga rida on kuu ja lühike silt.

Silt ei ütle, miks praak kasvas. Selle otsustab etapp 9.

## Etapp 7. Koosoleku lahtivõtt

Eesmärk on näidata ühe numbri tagust, ilma teist sõnumit tegemata.

Skript on `scripts/brief.py`. Ta loeb erindeid ja agregaate. Väljund on `work/05_koosolek/`.

Eraldi failid:

- `ulekulu_osad.csv` — mahakandmine, ümbertegemine, kliendileid
- `maht_vs_maar.csv` — suurem toodang, kõrgem määr, teistsugune tükihind
- `kuud.csv` — iga kuu eraldi
- `kuude_vordlus.csv` — kõige kallim kuu ja suurima hüppe kuu
- `muutumatu.csv` — mis fookustootel jäi paigale, mis liikus, mis on uus
- `kliendileid_liinil.csv` — sama defekt, kui see oleks jäänud liinile, koos eeldusega
- `baas.csv` — sama leid ühe, kahe ja kolme kuu baasil
- `index.md` — kas leid jääb samaks või lõige vahetub

Kui kallim kuu ja hüpe ei lange kokku, on mõlemad kirjas. Kui toode jääb samaks ja kitsam lõige vahetub, öeldakse mõlemat.

## Etapp 8. Visand

Eesmärk on üks pilt kümneks minutiks.

Skript on `scripts/sketch.py`. Ta loeb toodete agregaati ja `work/01_sundmused.json`.

Väljund on `output/joonis.svg`. Vasakul on määr kuude lõikes, kuude all juhendi sündmused. Paremal on ülekulu toodete lõikes. Märked on sündmused, mitte järeldus.

Päris pildid ei ole selles näites. Need jäävad kolmandasse faasi.

## Etapp 9. Hüpoteesid

Eesmärk on otsustada põhjus, mitte jätta sümptom sõnumisse.

Selle etapi teeb agent. Kuni kolm hüpoteesi. Allikas on erindid ja kontekst. Väljund on `work/04_hupoteesid.md`.

Igal hüpoteesil on väide, mida andmed näitaksid kui see peab, mida need näitaksid kui see ei pea, tulemus ja viide tabelile. Tulemus on kinnitatud, tagasi lükatud või ei otsusta.

Uus lõige salvestatakse `work/kusimused/` csv-na. Sündmus, mis testis läbi kukub, jääb tagasi lükatuks. Seda ei kirjutata põhjuseks.

## Etapp 10. Sõnum ja vastuste leht

Eesmärk on üks kõneldav sõnum ja leht, kust koosolekul vastata.

Selle etapi teeb agent. Väljund:

- `output/juhatuse_sonum.md`
- `output/vastuste_leht.md`

Sõnumis on viis lahtrit.

| Lahter | Mida sinna pannakse |
| --- | --- |
| Mis juhtus | Üks lause. Esimene asi, mille juhatusele ütled. |
| Mis see maksab | Üks number ja valem etapi 5 failist. |
| Miks see juhtus | Põhjus, mille etapp 9 kinnitas. |
| Mida juba teeme | 1–2 mustandit. Sõna MUSTAND on ees. |
| Mida juhatuselt vajan | Üks otsus. Mustand. |

Mustandid kirjutab kasutaja 45 minuti jooksul oma sõnadega üle.

Vastuste leht nimetab iga numbri faili, ütleb mis väite ümber lükkaks, annab kuni viis järelküsimust ja ühe rea tagasi lükatud hüpoteeside kohta. Leht viitab etapi 7 failidele.

## Etapp 11. Koosoleku küsimus

Eesmärk on vastata saalis, ilma analüüsi uuesti käivitamata.

See etapp algab siis, kui `work/03_outlierid.md` on juba olemas ja kasutaja küsib edasi.

Agent loeb ainult selle kausta tabeleid. Uus lõige läheb `work/kusimused/` alla. Küsimus ja vastus lisatakse faili `work/kusimused/kusimused.md`. Suusõnalist numbrit ei anta. Kui hind ei ole Excelis, ütleb kasutaja selle ise.

## Kuidas näidis kokku pandi

Ehitamise järjekord on sama mis käigu järjekord. Iga tükk pandi tööle enne järgmist.

1. Kausta skript ja `/create-folder`.
2. Kirjelduse skript, puhastus ja klappimine.
3. Agregaatide ja erindite skriptid.
4. `/analyse-data`, mis seob skriptid etappidega 3, 9 ja 10.
5. Vastuvõtt kaustas `analyses/2026_H1` näidisfailiga. Kui leid ei tulnud meetodist, parandati meetodit.
6. Koosoleku lahtivõtt, visand ja teine, simuleeritud andmestik. Simulatsiooni tõefail ei läinud `input/` kausta. Sõnumit võrreldi tõega pärast.

Näidisfail on `sample_data/` all. Kood ei sisalda selle faili toodete, tarnijate ega sündmuste nimesid. Tuntud lugu on vastuvõtu kontroll, mitte reegel.
