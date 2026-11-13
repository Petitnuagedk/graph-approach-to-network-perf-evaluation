# A4.4 static baseline report

G0 PASS: frame rate 1.0; positive pair count is floor(x+0.5); expected flows N=42/92/162 are 43/63/85.
G-A PASS: amended cap 340; historical accounting 305/310; 30 re-attempts charged under amendment 1; accounting total 335/340.
G-B PASS: amendment smoke verified directory creation and configuration writing; the dry-run constructed the command without invoking ns-3.
G-C PASS: warm-up/post/window are 120/180/320 s + 300 s; fixed windows [warm-up,warm-up+300].
G-D PASS: no A4.3 run reused; first pre-launch failures remain separate from amendment-1 rows.

Plan: 5 families × 3 sizes × 2 protocols = 30 rows; AODV 15 and OLSR 15; DSDV excluded by user direction.
Baseline card: phi is matched on forwarded-load proxy only, not flows per node; proxy uses geodesic path length for all families and is approximate.

Amendment-1 results: 30/30 ns-3 runs completed successfully; per-run CSV contains PDR, delay, per-type control packets/bytes and AODV RERR, forwarded-load Gini, MAC retries, PHY collision drops, readiness, elapsed, worker, exit code, and configuration hash.

- ba,N=42,aodv,phi=0.05: probe=1, bgmed=0.998824912, bgp10=0.99272533, delaymed=0.000524455, controlB/node=35761.7143, retriesMax=1345, collisionMax=8689, flag=none, elapsed=208.821756s, status=success.
- ba,N=42,olsr,phi=0.05: probe=0.974579585, bgmed=0.989041096, bgp10=0.975823577, delaymed=0.000524441, controlB/node=85759.9048, retriesMax=779, collisionMax=5985, flag=none, elapsed=197.69247s, status=success.
- ba,N=92,aodv,phi=0.015: probe=0.232295587, bgmed=0.284149264, bgp10=0.110532694, delaymed=0.199946819, controlB/node=1489127, retriesMax=43194, collisionMax=1307449, flag=none, elapsed=2408.53763s, status=success.
- ba,N=92,olsr,phi=0.015: probe=0.325692781, bgmed=0.198836413, bgp10=0.083789837, delaymed=0.020628345, controlB/node=128903.478, retriesMax=22325, collisionMax=343540, flag=none, elapsed=777.304855s, status=success.
- ba,N=162,aodv,phi=0.0065: probe=0.130757014, bgmed=0.180445151, bgp10=0.076222027, delaymed=0.342130887, controlB/node=2731826.21, retriesMax=57337, collisionMax=2859123, flag=none, elapsed=9455.67593s, status=success.
- ba,N=162,olsr,phi=0.0065: probe=0.195341451, bgmed=0.247217806, bgp10=0.0897959184, delaymed=0.0736707035, controlB/node=357666.642, retriesMax=28844, collisionMax=649993, flag=none, elapsed=2621.51109s, status=success.
- er,N=42,aodv,phi=0.05: probe=0.750879937, bgmed=0.999608611, bgp10=0.997023723, delaymed=0.000808283, controlB/node=34285.9048, retriesMax=476, collisionMax=4437, flag=none, elapsed=194.287018s, status=success.
- er,N=42,olsr,phi=0.05: probe=0.974579585, bgmed=0.989036805, bgp10=0.974135894, delaymed=0.000524645, controlB/node=123056.095, retriesMax=777, collisionMax=3012, flag=none, elapsed=177.186157s, status=success.
- er,N=92,aodv,phi=0.015: probe=0.988710229, bgmed=0.998631075, bgp10=0.993969223, delaymed=0.00080882, controlB/node=66756.4565, retriesMax=4631, collisionMax=18505, flag=none, elapsed=606.714745s, status=success.
- er,N=92,olsr,phi=0.015: probe=0.960314745, bgmed=0.97021568, bgp10=0.963919152, delaymed=0.000808705, controlB/node=282362.783, retriesMax=7038, collisionMax=27155, flag=none, elapsed=565.834s, status=success.
- er,N=162,aodv,phi=0.0065: probe=0.973530969, bgmed=0.997615262, bgp10=0.985281677, delaymed=0.000808706, controlB/node=138503.309, retriesMax=1818, collisionMax=18494, flag=none, elapsed=1679.13767s, status=success.
- er,N=162,olsr,phi=0.0065: probe=0.903652726, bgmed=0.925562914, bgp10=0.904123432, delaymed=0.000808724, controlB/node=567728.519, retriesMax=9759, collisionMax=45241, flag=none, elapsed=1865.33389s, status=success.
- geodesic,N=42,aodv,phi=0.05: probe=0.992569417, bgmed=0.999215994, bgp10=0.997258557, delaymed=0.001092283, controlB/node=28228.1429, retriesMax=3316, collisionMax=4558, flag=none, elapsed=268.639002s, status=success.
- geodesic,N=42,olsr,phi=0.05: probe=0.974970669, bgmed=0.976880878, bgp10=0.974933416, delaymed=0.000808569, controlB/node=95348.0952, retriesMax=406, collisionMax=1776, flag=none, elapsed=247.12562s, status=success.
- geodesic,N=92,aodv,phi=0.015: probe=0.995552515, bgmed=0.999315771, bgp10=0.996574638, delaymed=0.001376382, controlB/node=39781.6522, retriesMax=7802, collisionMax=9384, flag=none, elapsed=785.704609s, status=success.
- geodesic,N=92,olsr,phi=0.015: probe=0.971604516, bgmed=0.975684932, bgp10=0.9732895, delaymed=0.00137633, controlB/node=287169, retriesMax=7745, collisionMax=9815, flag=readiness_after_warmup, elapsed=779.578096s, status=success.
- geodesic,N=162,aodv,phi=0.0065: probe=0.99973531, bgmed=0.998144712, bgp10=0.995233556, delaymed=0.001516123, controlB/node=50056.2346, retriesMax=6664, collisionMax=11358, flag=none, elapsed=2228.11585s, status=success.
- geodesic,N=162,olsr,phi=0.0065: probe=0.943620963, bgmed=0.967930029, bgp10=0.954473232, delaymed=0.001944385, controlB/node=564938.568, retriesMax=8183, collisionMax=21297, flag=none, elapsed=2552.81266s, status=success.
- rgg,N=42,aodv,phi=0.05: probe=0.996089167, bgmed=0.99960815, bgp10=0.987323576, delaymed=0.000808839, controlB/node=28967.4762, retriesMax=289, collisionMax=1678, flag=none, elapsed=253.354898s, status=success.
- rgg,N=42,olsr,phi=0.05: probe=0.974970669, bgmed=0.977272727, bgp10=0.974925558, delaymed=0.000808708, controlB/node=60992.2857, retriesMax=507, collisionMax=918, flag=none, elapsed=236.090911s, status=success.
- rgg,N=92,aodv,phi=0.015: probe=0.996920972, bgmed=0.998972251, bgp10=0.996302402, delaymed=0.001377003, controlB/node=36131.7174, retriesMax=5679, collisionMax=10816, flag=none, elapsed=780.278255s, status=success.
- rgg,N=92,olsr,phi=0.015: probe=0.976052001, bgmed=0.97840987, bgp10=0.976394116, delaymed=0.001377039, controlB/node=166306.565, retriesMax=5447, collisionMax=9829, flag=none, elapsed=771.576862s, status=success.
- rgg,N=162,aodv,phi=0.0065: probe=0.997088407, bgmed=0.998144221, bgp10=0.994012189, delaymed=0.001945334, controlB/node=60524.3333, retriesMax=3838, collisionMax=12984, flag=none, elapsed=2563.28647s, status=success.
- rgg,N=162,olsr,phi=0.0065: probe=0.979883536, bgmed=0.980922099, bgp10=0.977072996, delaymed=0.001945371, controlB/node=293054.617, retriesMax=7373, collisionMax=13722, flag=none, elapsed=2589.95832s, status=success.
- ws,N=42,aodv,phi=0.05: probe=0.998044583, bgmed=1, bgp10=0.997256408, delaymed=0.001092296, controlB/node=27455.2381, retriesMax=1886, collisionMax=2685, flag=none, elapsed=252.790847s, status=success.
- ws,N=42,olsr,phi=0.05: probe=0.969495503, bgmed=0.975743349, bgp10=0.97348045, delaymed=0.001092272, controlB/node=66209.1429, retriesMax=696, collisionMax=1050, flag=none, elapsed=236.79782s, status=success.
- ws,N=92,aodv,phi=0.015: probe=0.998289429, bgmed=0.99760356, bgp10=0.978703155, delaymed=0.002228228, controlB/node=41816.4348, retriesMax=11754, collisionMax=18483, flag=none, elapsed=1012.20457s, status=success.
- ws,N=92,olsr,phi=0.015: probe=0.97194663, bgmed=0.976377953, bgp10=0.96961613, delaymed=0.001944489, controlB/node=126589.783, retriesMax=12415, collisionMax=18508, flag=none, elapsed=976.299989s, status=success.
- ws,N=162,aodv,phi=0.0065: probe=0.836686077, bgmed=0.997613998, bgp10=0.976521797, delaymed=0.00279642, controlB/node=53286.3333, retriesMax=13554, collisionMax=16675, flag=none, elapsed=3194.20884s, status=success.
- ws,N=162,olsr,phi=0.0065: probe=0.687136051, bgmed=0.844197138, bgp10=0.739234838, delaymed=0.00293814, controlB/node=234923.111, retriesMax=20484, collisionMax=52641, flag=none, elapsed=3464.58293s, status=success.

written after A4.4 results: the baseline card is descriptive and is not a ranking or ceiling.
STOP: no further phi, detector/window changes, DSDV, or Beta execution.

## A4.3-style plots applied to A4.4

The A4.3 plotting concept was adapted without introducing an artificial phi sweep: A4.4 has one registered phi per N, so each figure uses graph family on the x-axis and protocol as the style. Six plots were written for each of N=42, N=92, and N=162 under [plots_a44](plots_a44/), for 18 plots total. The plotting script is [plot_a44.py](plot_a44.py). These are descriptive visualizations of the amended A4.4 ledger and do not change the registered outcomes.

The proper A4.3-style hierarchy is [plots_amendment_1](plots_amendment_1/), containing exactly three folders: `plots/`, `graph_characteristic_plots/`, and `architecture_plots/`. Redundant N42/N92/N162 folders were removed. The five primary metric plots and five graph-characteristic plots use network size N on X and graph family/topology as the colored curves; AODV and OLSR use separate markers and line styles. Architecture snapshots are one figure for each N, with the five family topologies shown as node-edge diagrams. There are 14 plots total plus the index, and every plot has an explicit legend. The runner is [plot_a44_proper.py](plot_a44_proper.py). The earlier plot sets are retained only outside this proper output hierarchy and are not used as the final A4.3-equivalent set.
