selles projektis ma tahan ehitada ai agendi, mis võimldab regulaarselt analüüsida tootmise kvaliteedi andmed

ma hakkn seda kasutama korra nädalas juhatuse koosoleku ettevalmistamisel.

minu ülesanne on saada aru möödunud perioodi andmetest ning leida nenedest olulised sõnumid juhatusele.

Arendamise käigus on mul kasutada teatud andmestik, milles on mõned leiud olemas ja teada. samas järgises perioodis võivad olla leiud erinevad.
näite andmed on kataloogis sample_data

ma tahan teha sellise lahenduse, mis võimaldab mul mu aru saada andmetest eeldusel, et ma ei tea milline muster seal sees on

ma pean tulemuseks koostama juhatusele sõnumid ja ettepaneku 

Juhatusele | mõeldud sõnumid
Lahter	Mida sinna kirjutada
Mis juhtus	| Üks lause. Nii, nagu ütleksid selle juhatusele esimese asjana.
Mis see maksab	| Üks number + arvutuskäik.
Miks see juhtus |	Põhjus, mitte sümptom.
Mida juba teeme	| 1–2 tegevust, mis on sinu enda kontrolli all.
Mida juhatuselt vajan	| Üks konkreetne otsus, ressurss või mandaat.

minu ülesandeks on teha nii, et ma saan ise nendest armetest aru - ja oskan ka vajadusel kiirelt vastata.
ehk ülesanne pole mitte vastata ainlt küsimustele vaid võimaldada mul toetada ka juhatuse vestlust andmetega, mis on AI agendi poolt välja toodud.

mul on enne juhatuse koosolekut 45 min aega, et andmetesse süveneda ja vajalikus ulatuses leitud väljunedid kontrollida.

Ma tahan, et analüüs oleks etapiline ning iga etapi väljud oleks eraldi salvesatatud
analüüs toimub alati sama sturktuuri järgi 
- ai agent analüüsi kirejldavalt anmdmeid
- ai agent teeb andmetest agregatsiooni kokkuvõtted 
- ai agent otsib välja eristuvad outlierid
- ai agent püstitab hüpoteesid ja kontrollib neid

Iga analüüs paigutatakse eraldi kataloogi
antud kataloogis hoitakse sisend ja väljund andmeid

ilmselt peaks olema skill kataloogi puu haru loomiseks, mina siis kopeerin sinna andmed ja käivitan analüüsi
analüüsi vahetulemused pannakse eraldi alamkataloogi
juhatuse sõnum aga väljundkataloog

ma tahan teha sellised skillid
/create-folder -> loob folder struktuuri 
/analyse-data <folder> <file path>

analüüsiks ma olen paigaldanud pythoni keskkonna .venv kataloogi. palun kasuta seda
