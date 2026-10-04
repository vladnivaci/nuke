# Checklist inainte de publicare

Se parcurge integral inainte de fiecare deploy. Daca un punct pica, nu se publica.

## Structura

- [ ] `index.html` este in radacina, scris cu litere mici
- [ ] Niciun nume de fisier nu contine spatii
- [ ] Versiunile vechi sunt in `archive`, nu in radacina
- [ ] Media este in `assets`

## Legaturi si media

- [ ] Videoclipul se incarca si porneste la scroll
- [ ] Imaginea stickerului se incarca
- [ ] Numele fisierelor din cod corespund exact celor din repo, inclusiv
      literele mari si mici, pentru ca serverul face diferenta iar macOS nu
- [ ] Adresa de email din formular nu mai este cea de test
- [ ] Linkul de programare este completat, altfel butonul ramane ascuns

## Design

- [ ] Nicio culoare in afara paletei din `design-system.md`
- [ ] Rosu apare exclusiv la starea LOST
- [ ] Doar cele doua familii de font
- [ ] Textul nu se suprapune peste video sau imagini
- [ ] Animatiile respecta lista din `principles.md`

## Comportament

- [ ] Pe mobil povestea se intelege, chiar daca animatia este simplificata
- [ ] Nimic nu iese lateral din ecran
- [ ] Formularul semnaleaza campurile obligatorii necompletate
- [ ] Pagina arata corect si daca videoclipul nu se incarca

## Dupa publicare

- [ ] Adresa de productie se deschide fara eroare 404
- [ ] Se verifica pe un telefon real, nu doar prin redimensionarea ferestrei
