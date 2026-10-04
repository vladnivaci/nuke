# Design system

Valorile de mai jos sunt singurele permise in proiect. Sunt definite ca variabile
CSS in `index.html`, in blocul `:root`. Daca o valoare noua este necesara, se
adauga intai aici, apoi in cod.

## Culori

Paleta este monocroma. Nu exista culori de brand in afara acestei liste.

| Token | Valoare | Unde se foloseste |
|---|---|---|
| `--white` | `#ffffff` | Fundal principal, fundal sectiuni deschise |
| `--paper` | `#f6f6f4` | Fundal alternativ, separa sectiunile intre ele |
| `--line` | `#e2e2df` | Linii, borduri, separatoare |
| `--gray` | `#8a8a86` | Text secundar, subtitluri |
| `--gray-dark` | `#57574f` | Text de corp pe fundal deschis |
| `--ink` | `#17171a` | Text principal, elemente negre |
| `--black` | `#0a0a0b` | Fundal sectiuni inchise (lost/found, CTA final) |
| `--lost` | `#d6402c` | Exclusiv pentru starea LOST |

Regula rosului: `--lost` apare doar acolo unde se comunica pierderea unui bagaj.
Nu se foloseste pentru butoane, linkuri, accente sau erori decorative.

## Tipografie

Doua familii, cu roluri separate.

- **Space Grotesk** pentru logo, titluri, numere si etichete scurte. Geometric,
  rotunjit, se potriveste cu forma wordmark-ului `nuke`.
- **Inter** pentru text de corp si text de interfata.

Logo-ul `nuke` se scrie intotdeauna cu litera mica.

Marimile folosesc `clamp()`, ca sa scaleze intre mobil si desktop fara
breakpoint-uri separate. Exemplu din pagina: titlu hero
`clamp(26px, 4.2vw, 44px)`.

## Spatiere

Sectiunile folosesc padding vertical de `clamp(100px, 14vh, 160px)`.
Spatiul alb este un element de design, nu loc gol de umplut.

## Forme

- Raza colturilor pentru carduri si casete: `18px` pana la `22px`
- Raza butoanelor: `100px`, adica forma de pastila
- Grosimea liniilor: `1px`, capete rotunjite la liniile de indicatie

## Miscare

Toate tranzitiile folosesc `--ease: cubic-bezier(.22,.61,.36,1)`.
Durate intre `0.3s` si `0.6s` pentru interactiuni, pana la `2.4s` pentru
animatia de ripple.
