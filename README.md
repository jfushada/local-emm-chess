# Local Subgroup Discovery on a Lichess Player Network

2AMM20 research project, EMM Group 7. We're extending Local Subgroup Discovery on
Attributed Network Graphs (Heinrich et al., 2025) from binary to numerical
targets and applying it to a network of Lichess players.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Running

All commands from the repo root.

```bash
python -m src.features          # build players.csv and players_all.csv
python -m src.edges             # build edges_all.csv and edges_core.csv (run after features)
python -m src.tabular_mining    # subgroup discovery on the player table
python -m pytest                # run the tests
```

## Structure

```
src/
  config.py            shared paths and settings (filters, growth windows)
  features.py          builds the player tables (attributes + targets)
  edges.py             builds the edge lists of the player network
  quality_measures.py  quality measures for numerical targets (mean-based, KS)
  tabular_mining.py    subgroup discovery on the player table, no network
algorithm/
  methods.py           network-based local subgroup discovery (adapted from LSD-ATNG)
data/
  raw/                 crawled Lichess data
  processed/           generated files (players.csv, players_all.csv, edges_*.csv)
tests/                 tests for quality measures and tabular mining
results/               figures and tables for the paper
```

## Player table: `data/processed/players.csv`

One row per crawled ("core") player, 150 in total. Built by `src/features.py`.

- **Sampled games** = the ~50 most recent rated games per player that we downloaded
  (bullet, blitz, rapid, classical; no variants, no simuls, no games under 4 half-moves).
- **Main time control** = the time control with the most sampled games.
- **Reference date** = the date of the most recent game in the data (Oct 7, 2026).
  Account age and all growth windows are measured up to this date, so results don't
  depend on when the script is run.

### Attributes

| Column                                       | Meaning                                                                                             | Source  |
| -------------------------------------------- | --------------------------------------------------------------------------------------------------- | ------- |
| `username`                                   | Lichess username, lowercase                                                                         | profile |
| `n_games`                                    | number of sampled games (see note below)                                                            | games   |
| `win_rate`                                   | share of sampled games won                                                                          | games   |
| `draw_rate`                                  | share of sampled games drawn                                                                        | games   |
| `avg_moves`                                  | average game length in moves (half-moves / 2)                                                       | games   |
| `share_bullet`, `share_blitz`, `share_rapid` | share of sampled games per time control (sum to 1)                                                  | games   |
| `opponents_per_game`                         | distinct opponents / sampled games; near 1 = many different opponents, near 0 = mostly the same few | games   |
| `opening_diversity`                          | entropy (bits) over opening families played; 0 = always the same opening                            | games   |
| `main_tc`                                    | most played time control in the sampled games: `bullet`, `blitz` or `rapid`                         | games   |
| `rating`                                     | rating in the most recent sampled game in the main time control                                     | games   |
| `account_age_days`                           | days from account creation to the reference date                                                    | profile |
| `title`                                      | Lichess title (`GM`, `IM`, `FM`, `CM`, `NM`), or `none`                                             | profile |
| `games_bullet`, `games_blitz`, `games_rapid` | total rated games ever played per time control                                                      | profile |

Only players with at least 50 rated games in their main time control (profile totals)
are included. All 150 crawled players pass this filter.

### Targets

| Column                                             | Meaning                                                                                                                    |
| -------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `target_growth_3m`                                 | **main target**: rating change over the 3 months before the reference date, in the main time control                       |
| `target_growth_1m`, `target_growth_6m`             | the same over 1 and 6 months                                                                                               |
| `target_growth_games`                              | rating change between the first and last sampled game in the main time control (usually only 2–3 weeks, so mostly noise)   |
| `target_growth_1m_top20`, `_3m_top20`, `_6m_top20` | binary version: 1 if in the top 20% by growth for that window, 0 otherwise (for comparing with the original binary method) |

The 1/3/6-month targets come from the full rating history. They are **empty (NaN)**
when growth can't be measured reliably:

- the player had fewer than 10 days with rating changes in their main time control
  before the window started (new account, or barely played that time control), so
  the starting rating isn't trustworthy yet
- the player didn't play their main time control during the window

Players with an empty target should be skipped for that target, not treated as 0.

### Columns to exclude per target

Some columns contain information about the target. Using them as attributes (for
mining conditions or for Gower tie-breaking) makes results meaningless.

| Target                                  | Exclude                                                  |
| --------------------------------------- | -------------------------------------------------------- |
| any                                     | `username`, `n_games`, all other `target_*` columns      |
| rating growth (`target_growth_*`)       | `rating` (current rating is the end point of the growth) |
| opening diversity (if used as target)   | `opening_diversity`                                      |
| average game length (if used as target) | `avg_moves`                                              |
| versatility (if used as target)         | `share_*` columns                                        |

`n_games` is ~50 for everyone because of how the data was crawled, so it describes our
data collection, not the player. It's kept in the table as a sanity check only.

## All players: `data/processed/players_all.csv`

Core players **and** their opponents: 5,100 players (150 core + 4,950 opponents).
Built by `src/features.py`. Used as the node table for the network experiments.

Opponents only appear in ~1 sampled game each (against a core player), so
game-based attributes would be meaningless for them. This table therefore only has
columns that are reliable for everyone, from the profiles and the rating history:

| Column                                                                    | Meaning                                                                                                                                           |
| ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `username`                                                                | Lichess username, lowercase                                                                                                                       |
| `is_core`                                                                 | True for the 150 crawled players, False for opponents                                                                                             |
| `account_age_days`, `title`, `games_bullet`, `games_blitz`, `games_rapid` | as in `players.csv`                                                                                                                               |
| `main_tc`                                                                 | time control with the most days with rating changes in the 3 months before the reference date (falls back to lifetime profile totals if inactive) |
| `rating`                                                                  | last rating on or before the reference date, in the main time control                                                                             |
| `target_growth_1m/3m/6m` and `_top20`                                     | as in `players.csv` (same windows, same minimum-history check)                                                                                    |

Only players who appear in at least one cleaned game are included, so every node has
at least one edge. The 50-game filter applies here too.

**Note:** `main_tc` is defined differently than in `players.csv` (rating history vs.
sampled games), so it can differ for some core players (16 of 150), and so can their
targets. Within each file, every player is treated the same way

The same columns to exclude apply as for `players.csv` (`rating` for rating growth,
other `target_*` columns always).

## Network: `data/processed/edges_all.csv`, `edges_core.csv`

One row per pair of players who played each other in the sampled games.
Built by `src/edges.py`, from the same cleaned games as the player tables.

| Column                 | Meaning                                                  |
| ---------------------- | -------------------------------------------------------- |
| `player_a`, `player_b` | the two players, alphabetical, so each pair appears once |
| `n_games`              | number of games between them                             |
| `distance`             | 1 / `n_games`: frequent opponents are close              |

| File             | Nodes                                | Edges |
| ---------------- | ------------------------------------ | ----- |
| `edges_all.csv`  | players in `players_all.csv` (5,100) | 5,857 |
| `edges_core.csv` | players in `players.csv` (150)       | 289   |

Things to know about the network:

- **No opponent–opponent edges.** We only downloaded the games of the core players,
  so every edge contains at least one core player. The network looks like ~150 stars:
  a core player with their (mostly one-off) opponents around them.
- **Most pairs played once:** 92% in `edges_all`, 73% in `edges_core`.

## Data notes

- **Usernames** are lowercase in all processed files. Raw files can have mixed case
  (e.g. `NihalSarin`), so lowercase before joining.
- **Rating history months** are 1–12 in our raw files (the Lichess API itself uses 0–11).
