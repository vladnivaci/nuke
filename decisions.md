# Jurnal de decizii

Fiecare intrare are trei randuri: contextul, decizia, consecinta.
Se adauga o intrare noua la fiecare decizie de design care nu este evidenta.

---

## 001 Animatia hero este controlata de scroll, nu de timp

**Context:** Un video care porneste singur ruleaza la fel indiferent de ce face
vizitatorul, iar relatia cu obiectul se pierde.

**Decizie:** Pozitia scroll-ului conduce direct `video.currentTime`. La 30% din
sectiune, videoclipul este la 30%. La urcare, revine inapoi.

**Consecinta:** Vizitatorul simte ca manipuleaza obiectul. Costul este ca pe
mobil scrubbing-ul video este inconstant intre browsere, deci acolo se
simplifica.

---

## 002 Titlul este un panou separat, nu text peste video

**Context:** Prima varianta avea titlul suprapus peste animatie. Textul si
produsul concurau pentru acelasi spatiu si niciunul nu era lizibil.

**Decizie:** Titlul sta pe un panou alb opac care acopera tot ecranul, si
dispare printr-un scroll scurt, primele 8% din sectiune.

**Consecinta:** Animatia porneste pe ecran liber si nu este taiata. Costul este
un scroll in plus inainte sa inceapa povestea.

---

## 003 Predarea de la video la imagine se face cu acelasi cadru

**Context:** Tranzitia de la finalul videoclipului la stickerul 2D se vedea ca
o taietura.

**Decizie:** Imaginea PNG folosita ca overlay este chiar cadrul final dat
modelului la generare. Videoclipul si imaginea stau in aceeasi caseta, cu
acelasi `object-fit`.

**Consecinta:** Suprapunere pixel cu pixel, tranzitie invizibila. Costul este ca
orice regenerare a videoclipului cere regenerarea perechii.

---

## 004 Rosul este rezervat starii LOST

**Context:** Paleta este monocroma, dar momentul pierderii bagajului are nevoie
de tensiune vizuala.

**Decizie:** `--lost` se foloseste doar pentru eticheta LOST si pentru contorul
de bagaje pierdute din dashboard.

**Consecinta:** Cand apare rosu, inseamna ceva. Costul este ca nu exista culoare
de accent disponibila pentru altceva.

---

## 005 Formularul de contact trimite prin email, fara backend

**Context:** Gazduirea este statica pe Vercel, deci nu exista server care sa
primeasca formulare.

**Decizie:** Formularul compune un email precompletat si il deschide in aplicatia
de mail a vizitatorului. Separat, un buton de programare deschide pagina de
Google Calendar Appointment Schedule.

**Consecinta:** Functioneaza fara infrastructura. Costul este ca vizitatorul
trebuie sa apese Send, iar fara aplicatie de mail configurata pasul esueaza.
