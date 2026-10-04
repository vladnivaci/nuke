# nuke

**Lost bags find their way.**

NUKE da fiecarui bagaj de cala o identitate digitala, ca bagajele pierdute sa fie
mai usor de identificat, localizat si returnat, fara ca pasagerul sa fie nevoit
sa faca ceva.

Produsul fizic este un sticker ieftin cu NFC, cod QR si un identificator unic,
aplicat de aeroport la check-in. Stickerul nu contine date personale, ci doar un
token securizat care face legatura cu sistemul aeroportului. Modelul este B2B:
aeroporturile si companiile aeriene platesc, pasagerul primeste serviciul gratuit.

Acest repository contine site-ul de prezentare.

## Structura

```
index.html              pagina publicata
README.md               fisierul de fata
/assets                 video si imagini folosite de pagina
/docs                   regulile de design
/archive                versiuni anterioare, pastrate ca istoric
```

## Documentatia de design

Inainte de orice modificare vizuala, se citesc fisierele din `docs`.

| Fisier | Ce contine |
|---|---|
| [design-system.md](docs/design-system.md) | Culorile, fonturile, spatierea si formele permise |
| [principles.md](docs/principles.md) | Ce trebuie si ce nu trebuie sa para site-ul |
| [decisions.md](docs/decisions.md) | De ce au fost luate deciziile de design |
| [checklist.md](docs/checklist.md) | Verificarile obligatorii inainte de publicare |

## Cum se modifica

1. Se citeste `docs/design-system.md` si `docs/principles.md`.
2. Se face modificarea in `index.html`.
3. Daca decizia nu este evidenta, se adauga o intrare in `docs/decisions.md`.
4. Se parcurge `docs/checklist.md`.
5. Commit si push. Publicarea se face automat.

## Tehnic

Pagina este un singur fisier HTML, fara dependinte si fara pas de build.
Fonturile vin de la Google Fonts. Animatia din sectiunea hero este legata de
pozitia scroll-ului.

Publicare: fisierul se serveste static din radacina repository-ului.
Framework Preset trebuie setat pe **Other**, iar Root Directory lasat gol.
