# Rakendamise plaan

Eesmärk on kord nädalas, 45 minutiga, jõuda ühe juhatuse sõnumini. Agent aitab andmetest aru saada ja koosolekul järele vastata. Ta ei otsi etteantud mustrit.

Näidisandmestik on `sample_data/Kvaliteedipäev 2026 Andmestik A Metaltek_praak_ja_korvalekalded_2026.xlsx`. Selles on teadaolev lugu. Järgmine periood võib olla teistsugune, seega kood ei tohi tunda tooteid, tarnijaid ega sündmusi. Tuntud lugu on ainult vastuvõtutest plaani lõpus.

## Otsused

- Lahendus on Cursori projekti skillid ja Python. Eraldi rakendust ei ehitata.
- Python käivitub ainult `.venv/bin/python`. Uusi teeke ei lisata. Kasutuses on pandas, openpyxl ja numpy.
- Skriptid teevad puhastuse, agregaadid ja erindite pingerea. Need on iga kord samad.
- Agent loeb skriptide väljundit, sõnastab hüpoteesid, kontrollib neid andmetega ja kirjutab juhatuse sõnumi.
- Väljund on eesti keeles.
- Skillid elavad projektis: `.cursor/skills/`. Need käivituvad ainult nimepidi (`/create-folder`, `/analyse-data`).
- Üks koosolek, üks sõnum. Kõrvalleidud jäävad vastuste lehele, et koosolekul oleks millega vastata.
- Rahanumber on halvenemise lisakulu nimetatud baasi suhtes, koos arvutuskäiguga. Kogu perioodi praagi summa ei ole sõnum.
- `Mida juba teeme` ja `Mida juhatuselt vajan` on mustandid. Agent ei tea, mida kasutaja juba teeb. Kasutaja kinnitab need 45 minuti jooksul.
- Eurot ei mõelda välja. Kui failis pole omahinda, tunnihinda ja kliendijuhtumi kulu, jääb rahanumber tegemata ja seda öeldakse otse.

## Kataloog

Iga analüüs on oma puu. Kasutaja kopeerib sinna faili, skill ei liiguta originaali `sample_data` alt ära.

```
analyses/<periood>/
  input/                         # kasutaja fail, skill ei kustuta
  work/
    01_kirjeldus.md
    01_kontekst.md               # lugemisjuhendist loetud taust
    01_hinnad.json               # ainult need numbrid, mis juhendis on
    01_tabelid/                  # puhastatud csv
    02_agregatsioonid/           # csv + index.md
    03_outlierid.md
    03_outlierid.json
    04_hupoteesid.md
    kusimused/                   # koosoleku järelküsimuste tabelid
  output/
    juhatuse_sonum.md
    vastuste_leht.md
```

`<periood>` on kasutaja antud nimi, näiteks `2026_Q2`. Nimes tohib olla tähti, numbreid, `_` ja `-`.

`/analyse-data` üle kirjutab `work/` ja `output/`. `input/` jääb puutumata.

## Andmete lugemine

Näidisfailis on kolm lehte. Järgmine fail võib olla sama kujuga, aga kood ei eelda Metalteki nimesid.

- Faktitabelid on need lehed, kus on veerupealkirjad ja korduvad read. Näidisel `Kuukokkuvõte` (kuu, toode, toodetud tk, praak tk, praakmäär) ja `Kõrvalekalded` (üksikud juhtumid).
- Tekstileht on see, mis on valdavalt laused. Näidisel `Lugemisjuhend`: tooted, omahind, müügihind, ümbertegemise aeg, tunnihind, kliendi juures avastamise lisakulu, ning perioodi sündmused. Sündmus ei ole põhjus enne, kui hüpotees seda andmetega kinnitab.
- Puhastusreegel, mis on üldine: kui rea tunnus ja kuupäev on mõlemad tühjad, ei ole see juhtum. Rida jäetakse välja ja `01_kirjeldus.md` ütleb, mitu rida ja mitu tükki välja jäi. Näidisel on registri lõpus kolm sellist rida (1483, 1425 ja 1615 tükki). Kui need sisse jätta, on tükkide summa vale.
- Pärast puhastust peab registri tükkide summa kuu ja toote lõikes klappima kuukokkuvõtte praagi tükkidega. Näidisel on mõlemad 1631. Kui vahe on suurem kui 1%, analüüs peatub. Juhatuse sõnumit ei kirjutata.
- Kui määra veeru kõik väärtused on 0 ja 1 vahel, on see suhe, mitte protsent. Väljundis näidatakse protsenti. Näidisel on `Praak %` suhe (0,0152 = 1,52%).

## Etapid

Iga etapp jätab faili maha enne, kui järgmine algab. Kasutaja saab vahepeal peatuda ja numbrit kontrollida.

### 1. Kirjeldus

Skript kirjutab iga lehe kohta ridade arvu, veerud, tüübid, tühjad väärtused, unikaalsete väärtuste arvu ja vahemiku. Tekstileht läheb `01_kirjeldus.md` lõppu tekstina.

Agent teeb sellest `01_kontekst.md` ja `01_hinnad.json`. Hinnajsonis on ainult juhendist loetud arvud, igaühel viide reale. Oodatav kuju, kui juhend need annab:

- toote omahind
- ümbertegemise minutid
- tunnihind
- kliendi juures avastatud juhtumi lisakulu

Kui mõni neist puudub, jääb väli tühjaks. Skript ei pane asemele näidisandmete numbreid.

### 2. Agregatsioonid

Skript teeb csv-d mõõtmete kombinatsioonidest, mis andmetes päriselt on. Näidisel: kuu, toode, defekti liik, vahetus, avastamise koht, tarnija, ümbertegemise lipp.

Iga agregaat sisaldab tükke, juhtumite arvu ja määra seal, kus on nimetaja (toodetud tk). Kui `01_hinnad.json` on olemas, lisandub euro veerg. Valem on failis näha:

- mahakandmine: tükid, millel ümbertegemise lipp on ei, korrutatud omahinnaga
- ümbertegemine: tükid, millel lipp on jah, korrutatud minutite, tunnihinna ja 1/60-ga
- kliendileid: juhtumite arv korda juhtumi lisakulu

Kasutatakse registri lippu, mitte juhendi ligikaudset “umbes 60% tehakse ümber”.

`02_agregatsioonid/index.md` loetleb failid ja ühe rea, mida iga fail näitab.

### 3. Erindid

Skript reastab lõigud. Meetod on fikseeritud, et järgmine nädal oleks võrreldav.

- Baas on ajatelje esimene kolmandik, aga vähemalt kaks esimest perioodi, kui perioode on vähemalt neli. Baas kirjutatakse väljundisse.
- Lõik on erind, kui määr baasi suhtes muutub ja tükkide või eurode muutus on materjali. Materjali tähendab: kuulub muutusest esimese viie sekka või annab vähemalt 20% kogu muutusest.
- Eraldi pingerida tükkide ja eurode järgi. Suur tükimaht ei ole sama mis kallis leid. Näidisel on tootel C kõige rohkem defektitükke ja kõige väiksem omahind.
- Kaasneb lühike nimekiri stabiilsetest lõikudest, mis paistavad suured, aga baasi suhtes ei muutu. Need ei lähe sõnumisse.

Väljund `03_outlierid.md` on pingerida: lõik, baas, praegune, muutus, euro kui see on olemas, ja viide csv reale.

### 4. Hüpoteesid

Agent püstitab kuni kolm hüpoteesi erindite ja konteksti pealt. Iga hüpotees saab testi, mis on uus lõige olemasolevatest tabelitest või `work/kusimused/` alla salvestatud csv.

Hüpoteesi rida:

- väide
- mida andmed peaksid näitama, kui väide peab
- mida andmed peaksid näitama, kui väide ei pea
- tulemus: kinnitatud, tagasi lükatud või ei otsusta
- viide tabelile

Konteksti sündmus, mis testis läbi kukub, jääb tagasi lükatuks. Seda ei tohi sõnumisse põhjuseks kirjutada. Näidisel on mitu sellist kandidaati (õhtune vahetus, maht, terase hind, juhi vahetus). Test peab ise näitama, milline neist klapib ajastusega ja milline mitte.

### 5. Väljund

`output/juhatuse_sonum.md` on üks sõnum, viis lahtrit. Mall on ülesandest, sõnastus on kõnes:

| Lahter | Reegel |
| --- | --- |
| Mis juhtus | Üks lause. Esimene asi, mille juhatusele ütled. |
| Mis see maksab | Üks number ja arvutuskäik. Baas on nimetatud. |
| Miks see juhtus | Põhjus, mida hüpotees kinnitas. Sümptom ei kõlba. |
| Mida juba teeme | 1–2 mustandit, mis on kasutaja enda kontrolli all. Märge, et kasutaja kirjutab need oma sõnadega üle. |
| Mida juhatuselt vajan | Üks konkreetne otsus, ressurss või mandaat. Mustand. |

`output/vastuste_leht.md` on 45 minuti ja koosoleku tugi:

- sõnumi iga numbri allikas: fail, leht, filter
- mis selle väite ümber lükkaks
- kuni viis tõenäolist järelküsimust ja vastus koos viitega
- tagasi lükatud hüpoteesid ühe reaga, et “miks mitte X” oleks käepärast

Kui kasutaja küsib analüüsi kohta hiljem, vastatakse nendest failidest. Uus lõige salvestatakse `work/kusimused/` alla. Suusõnalist numbrit ei anta.

## Skillid

### `/create-folder <periood>`

Loob ülaltoodud puu. Kui puu on juba olemas, ei kustuta midagi ja ütleb seda. Lõpus öeldakse: kopeeri fail `analyses/<periood>/input/` alla ja käivita analüüs.

Skript: `.venv/bin/python scripts/create_folder.py <periood>`

### `/analyse-data <periood> <fail>`

1. Kontrollib, et perioodi puu on olemas. Kui ei ole, peatub ja ütleb, et enne on `/create-folder`.
2. Kopeerib faili `input/` alla, kui seda seal veel pole. Algfaili ei liiguta.
3. Käivitab järjekorras `scripts/profile.py`, `scripts/aggregate.py`, `scripts/outliers.py`.
4. Kui etapp 1 ütleb, et kuu ja register ei klapi, peatub.
5. Agent kirjutab konteksti, hinnad, hüpoteesid, sõnumi ja vastuste lehe.
6. Kui `work/03_outlierid.md` on juba olemas ja kasutaja küsib küsimuse, ei jooksutata etappe uuesti. Uus tabel läheb `work/kusimused/` alla.

Käsk ilma failita kasutab `input/` ainsat tabelifaili. Kui faile on mitu, küsib kasutajalt, milline.

## Skriptid

Kõik `scripts/` all, käivitatavad, tüübiviidetega, ilma liigsete kommentaarideta.

| Skript | Sisend | Väljund |
| --- | --- | --- |
| `create_folder.py` | perioodi nimi | kataloogipuu |
| `profile.py` | `analyses/<periood>` | kirjeldus, puhastatud csv, klappimise kontroll |
| `aggregate.py` | puhastatud csv, valikuline `01_hinnad.json` | `02_agregatsioonid/` |
| `outliers.py` | agregaadid | `03_outlierid.md` ja `.json` |

`profile.py` väljumiskood on 2, kui register ja kuukokkuvõte ei klapi. Skill ei lähe sellest edasi.

## Mida esimeses versioonis ei tehta

- Veebivaadet, andmebaasi ega ajastatud tööd.
- Automaatset “miks” ilma hüpoteesita.
- Mitut sõnumit ühe koosoleku jaoks.
- Graafikuid. Tabelist piisab, kuni kasutaja tahab slaidi.
- `requests` ja `bs4` jäävad `requirements.txt` sisse, aga analüüs neid ei kasuta.

## Vastuvõtutest

Pärast ehitust teeme ühe päris käigu: `/create-folder 2026_H1` ja `/analyse-data 2026_H1` näidisfailiga. `sample_data` jääb muutmata.

Meetod on korras, kui väljund ise, ilma Metalteki reegliteta koodis, näitab järgmist.

- Kolm tühja tunnusega rida on välja jäetud ja seda on kirjeldatud. Puhastatud register klapib kuukokkuvõttega: 1631 tükki.
- Praakmäär on loetud suhtena.
- Sõnum räägib halvenemisest, mitte suurimast tükimahust. Toote A praakmäär kasvab jaanuari umbes 1,5% pealt juuni 6,4% peale. Tooted B ja C püsivad 2% ümber.
- Kasv on pinnadefekt. Tarnija vahetub märtsis Pinnatek OÜ pealt Surfex AS peale. Pinnadefekti tükid: 6, 6, 29, 44, 63, 70.
- Kliendi juures leitud toote A juhtumid hüppavad mais. See on eraldi hüpotees, mitte sama väide mis märtsi pinnadefekt.
- Õhtune vahetus algab aprillis. Test peab saama kontrollida, et pinnadefekt kasvas juba märtsis. Kui test vahetust ei kinnita, ei ole vahetus sõnumi põhjus.
- Rahanumber on toote A lisakulu baasi suhtes, valem on kirjas, ja toode C ei võida pingerida ainult tükkide pärast.
- `Mida juba teeme` ja `Mida juhatuselt vajan` on märgitud mustandiks.

Kui mõni neist punktidest jääb tulemata, parandame meetodit, mitte vastust.

## Ehitamise järjekord

1. `scripts/create_folder.py` ja skill `/create-folder`.
2. `scripts/profile.py` koos puhastuse ja klappimise kontrolliga.
3. `scripts/aggregate.py` ja `scripts/outliers.py`.
4. Skill `/analyse-data`, mis seob skriptid ja kirjutab etapid 4–5.
5. Vastuvõtukäik `analyses/2026_H1` peal. Võrdlus ülaltoodud punktidega.
6. Parandus ainult seal, kus test ebaõnnestub.
