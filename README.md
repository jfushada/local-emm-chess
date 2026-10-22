# Numerical Quality Measures for Local Subgroup Discovery on Attributed Networks

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
python -m src.features          # build players.csv, players_all.csv and players_snowball.csv
python -m src.edges             # build edges_*.csv (run after features)
python -m src.tabular_mining    # subgroup discovery on the player table
python -m src.network_mining    # local subgroup discovery on the player network
python -m src.significance_test # permutation test for the best subgroup (slow, see below)
python -m src.describe_lichess_groups  # describe the best subgroup per measure (paper numbers)
python -m src.plot_network      # network figures in results/ (paper figure: network_snowball_core_paper.pdf)
python -m pytest                # run the tests
```

Synthetic experiments (see [Synthetic networks](#synthetic-networks)):

```bash
cd fake_node_generator && python main.py && cd ..   # generate the synthetic networks
python -m src.synthetic_recovery                     # how well the planted subgroups are found
python -m src.plot_synthetic                         # paper figure: results/synthetic_recovery.pdf
```

## Structure

```
src/
  config.py            shared paths and settings (filters, growth windows)
  features.py          builds the player tables (attributes + targets)
  edges.py             builds the edge lists of the player network
  quality_measures.py  quality measures: mean-based, KS (numerical), WRAcc (binary)
  tabular_mining.py    subgroup discovery on the player table, no network
  network_mining.py    local subgroup discovery on the player network
  significance_test.py permutation test for the best network subgroup
  plot_network.py      network figures
  plot_synthetic.py    figure of the synthetic results
  describe_lichess_groups.py  sizes, growth and ratings of the best Lichess subgroups
  synthetic_recovery.py      runs the search on the synthetic networks and scores
                             it against the planted subgroups
  check_planted_centre.py    diagnostic: the search started at each planted centre
algorithm/
  methods.py           network-based local subgroup discovery (adapted from LSD-ATNG)
fake_node_generator/   generator for synthetic networks with planted subgroups
  confiugrations/config.json   generator settings (communities, targets, grid)
  result/              generated networks (not in git; run main.py)
data/
  raw/                 crawled Lichess data
  processed/           generated files (players*.csv, edges_*.csv)
  generated/           first synthetic network (80 players), kept for reference
tests/                 tests for quality measures and tabular mining
results/               figures and tables for the paper
```

## Player table: `data/processed/players.csv`

One row per crawled ("core") player, 150 in total. Built by `src/features.py`.

- **Sampled games** = the ~50 most recent rated games per player that we downloaded
  (bullet, blitz, rapid, classical; no variants, no simuls, no games under 4 half-moves).
- **Main time control** = the time control with the most sampled games.
- **Reference date** = Oct 7, 2026, the date of the most recent game in the original
  crawl (`REFERENCE_DATE` in `config.py`). Account age and all growth windows are
  measured up to this date, and games played after it are ignored, so results don't
  depend on when the script is run or when a file was crawled.

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
targets. Within each file, every player is treated the same way.

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

## Snowball step: `players_snowball.csv`, `edges_snowball*.csv`

In the paper the 200 crawled opponents are called **extension players** ("snowball"
in the code and file names). The core crawl itself is also snowball sampling, so the
paper avoids the word for this step.

To get edges between opponents, 200 opponents were crawled as well: the 200 with the
most games against our core players. For each, their 60 most recent rated games in
standard time controls up to the reference date, plus profile and rating history
(`data/raw/additional_opponent_games.csv`, `200opponent_profiles.csv`,
`200opponent_rating_history.csv`). These files are only built if the snowball games
file exists; the files above don't change.

| File                      | Players                                 | Edges |
| ------------------------- | --------------------------------------- | ----- |
| `players_snowball.csv`    | 150 core + 196 snowball = 346           |       |
| `edges_snowball.csv`      | players in `players_all.csv` (5,100)    | 7,417 |
| `edges_snowball_core.csv` | players in `players_snowball.csv` (346) | 1,067 |

- **`players_snowball.csv`** has the same columns as `players.csv`, plus
  `is_snowball`. Core rows are identical to `players.csv`, except the `_top20`
  columns, whose threshold is recomputed over all 346 players. Snowball players are
  described by their own games: their most recent 50 before the reference date.
  Players with fewer than 20 such games are left out (4 of 200).
- **`edges_snowball.csv`** = `edges_all.csv` plus the snowball games between players
  already in `players_all.csv` (games against players we have no profile for are
  dropped). It adds 1,469 edges without a core player, and the network becomes one
  connected component (`edges_all.csv` has two: 4,274 + 826).
- **`edges_snowball_core.csv`** still splits into two groups (182 + 164), roughly
  blitz vs bullet.

## Network mining settings

All in `src/config.py`:

| Setting                   | Meaning                                                                                                      |
| ------------------------- | ------------------------------------------------------------------------------------------------------------ |
| `NETWORK_DATASET`         | which network to mine: `snowball` (346 players), `generated`, `all`                                          |
| `NETWORK_DATASETS`        | per dataset: player and edge files, target, categorical / ignored columns                                    |
| `NETWORK_QUALITY_MEASURE` | `mean`, `ks` (numerical target) or `wracc` (binary `_top20` target)                                          |
| `NETWORK_MIN_RHO`         | minimum size of the reference group ρ (40; 5 = original method, see below)                                   |
| `NETWORK_TOP_GROUPS`      | number of subgroups to keep after removing overlapping ones                                                  |
| `SCORE_TO_TEST`           | best q to test in `significance_test.py`: copy the exact value from the `network_mining` output, not rounded |
| `SIGNIFICANCE_N`          | number of permutations (500; each one reruns the whole search)                                               |

**Why `NETWORK_MIN_RHO`.** For each prototype, the search first picks ρ as the group
that differs most from the whole network, then σ inside ρ as the group that differs
most from ρ. With the original minimum of 5, ρ shrinks onto an exceptional group
itself (ρ = the 10 planted players when 10 are planted), and then no σ inside it
stands out. The original LSD-ATNG code does the same. With ρ ≥ 40 (twice the largest
planted subgroup) the planted subgroups are found; see below. The Lichess components
have 182 and 164 players, so every player can reach at least 40 others.

## Lichess results (paper)

Core + extension network (346 players), target `target_growth_3m`, ρ ≥ 40,
500 permutations. The paper reports raw (uncorrected) p-values.

| Measure | Target                   | Best q | p    | Mined groups (`results/mined_groups/`)                                | Permutation plot (`results/significance_tests/`)                         |
| ------- | ------------------------ | ------ | ---- | --------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| mean    | `target_growth_3m`       | 414.19 | 0.03 | `network_groups_snowball_target_growth_3m_mean_min_rho_40.csv`        | `significance_test_snowball_target_growth_3m_mean_min_rho_40.png`        |
| KS      | `target_growth_3m`       | 1.78   | 0.16 | `network_groups_snowball_target_growth_3m_ks_min_rho_40.csv`          | `significance_test_snowball_target_growth_3m_ks_min_rho_40.png`          |
| WRAcc   | `target_growth_3m_top20` | 0.22   | 0.14 | `network_groups_snowball_target_growth_3m_top20_wracc_min_rho_40.csv` | `significance_test_snowball_target_growth_3m_top20_wracc_min_rho_40.png` |

Tabular baseline (`src/tabular_mining.py`, 3m target): mean p = 0.67, KS p = 0.29
(`data/processed/permutation_results.csv`; top subgroups in
`data/processed/tabular_subgroups.txt`).

Only the `_min_rho_40` files are used in the paper. The other files in
`results/mined_groups/` and `results/significance_tests/` are earlier runs
(1- and 6-month windows, original ρ ≥ 5), kept for reference.

To reproduce a row, set `NETWORK_QUALITY_MEASURE` and the target of the
`snowball` dataset in `src/config.py`, run `src.network_mining`, copy the best `q`
into `SCORE_TO_TEST` and run `src.significance_test`. The defaults are the mean row.

## Synthetic networks

Generated by `fake_node_generator/main.py` with the settings in
`fake_node_generator/confiugrations/config.json`:

- **Network:** stochastic block model with 4 communities of 40 players
  (in-community edges more likely, more games per in-community edge).
- **Target:** normal per community (baselines -20, 15, 25, 30; sd 80).
- **Planted subgroups:** one per community, the `size` players nearest to a random
  centre (ranked like the search: shortest path, ties by Gower), with the target shifted by `shift` × sd.
- **Grid:** shift 0.5, 1, 2, 3 sd × size 5, 10, 20, with `N_SEEDS = 5` networks per
  setting (seed i = config seeds + i). Each network is saved in
  `result/network_range/shift_<shift>_size_<size>_seed_<i>/`, listed in `networks.csv`.
- **Binary target** `WKL_target_bin`: top 20% of the target, for the WRAcc baseline.

`src/synthetic_recovery.py` runs the search with mean, KS (on `target`) and WRAcc
(on `WKL_target_bin`) and, for each planted group, takes the best Jaccard overlap
with a σ among the top 20 results. The summary reports this as Dice similarity
(Dice = 2J / (1 + J)); a planted group counts as found if Dice ≥ 0.75. To change
the metric without rerunning the search: `python -m src.synthetic_recovery --summary`.
`src/plot_synthetic.py` makes the figure for the paper (`results/synthetic_recovery.pdf`).

| File (in `results/`)                         | Contents                                                                |
| -------------------------------------------- | ----------------------------------------------------------------------- |
| `synthetic_recovery_min_rho_<n>.csv`         | one row per network × measure × planted group                           |
| `synthetic_recovery_summary_min_rho_<n>.csv` | averaged per shift × size × measure; `found` = share with σ Dice ≥ 0.75 |

Main results (σ Dice similarity, averaged over sizes and seeds):

| Shift  | min ρ = 5 (mean, KS) | min ρ = 40: mean | KS   | WRAcc (binary) |
| ------ | -------------------- | ---------------- | ---- | -------------- |
| 0.5 sd | ~0.38                | 0.46             | 0.43 | 0.37           |
| 1 sd   | ~0.38                | 0.63             | 0.58 | 0.56           |
| 2 sd   | ~0.34                | 0.91             | 0.88 | 0.79           |
| 3 sd   | ~0.33                | 0.96             | 0.96 | 0.85           |

The binary measure falls behind mainly for size 20: 4 × 20 = 80 shifted players
against 32 marked as top 20%, so most planted players get a 0.

## Data notes

- **Usernames** are lowercase in all processed files. Raw files can have mixed case
  (e.g. `NihalSarin`), so lowercase before joining.
- **Rating history months** are 1–12 in our raw files (the Lichess API itself uses 0–11).
