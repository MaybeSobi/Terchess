# Third-party notices

Terchess uses third-party Python packages, including:

- **python-chess** — chess rules, notation, and engine communication.
- **Rich** — terminal formatting and display.
- **prompt-toolkit** — interactive terminal input.

Their licenses and notices are provided by the respective package distributions. Review the license metadata for the exact dependency versions installed in your environment.

## Stockfish

Terchess can communicate with a separately installed Stockfish engine through the UCI protocol. Stockfish is an independent project distributed under GPLv3. Terchess does not bundle the Stockfish executable. Download it from the [official Stockfish website](https://stockfishchess.org/download/) and review its license and notices there.

Terchess is licensed under GPL-3.0-or-later. This notice is informational and is not a substitute for the license files shipped with third-party software.


## Opening reference data

The bundled `src/terchess/data/openings.tsv` file is derived from the
[lichess-org/chess-openings](https://github.com/lichess-org/chess-openings)
project. The dataset is released under the
[CC0 1.0 Universal Public Domain Dedication](https://creativecommons.org/publicdomain/zero/1.0/).
Terchess uses this data locally and does not contact Lichess for opening recognition.
