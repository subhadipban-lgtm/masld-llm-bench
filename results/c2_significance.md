# C2 paired significance (McNemar exact + Wilcoxon signed-rank)

Verdicts at p < 0.05: accuracy -> McNemar, MAE -> Wilcoxon (better = lower).

## Candidate: qwen3-0.6b-masld (`qwen3-0.6b-masld__MB-20xx_PAIRED.jsonl.gz`)

39 comparisons — WIN 17 / LOSS 7 / TIE 15

| reference | task | metric | n | cand | ref | both | cand_only | ref_only | neither | mcnemar_p | wilcoxon_p | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| amazon | MB-2001 | accuracy | 168 | 0.4048 | 0.1131 | 7 | 61 | 12 | 88 | 4.802e-09 | 9.75e-09 | WIN |
| amazon | MB-2002 | accuracy | 168 | 0.1964 | 0.1726 | 13 | 20 | 16 | 119 | 0.6177 | 0.505 | TIE |
| amazon | MB-2003 | accuracy | 10 | 0.6 | 0 | 0 | 6 | 0 | 4 | 0.03125 | 0.03125 | WIN |
| amazon | MB-2005 | mae | 168 | 1.524 | 6547 | 41 | 83 | 44 | 0 | 0.0006846 | 0.0002361 | WIN |
| amazon | MB-2006 | mae | 167 | 4.731 | 9237 | 33 | 68 | 55 | 11 | 0.2792 | 0.002212 | WIN |
| deepseek | MB-2001 | accuracy | 163 | 0.3988 | 0.135 | 9 | 56 | 13 | 85 | 1.684e-07 | 2.26e-07 | WIN |
| deepseek | MB-2002 | accuracy | 163 | 0.1902 | 0.1718 | 14 | 17 | 14 | 118 | 0.7201 | 0.59 | TIE |
| deepseek | MB-2003 | accuracy | 258 | 0.469 | 0.3992 | 60 | 61 | 43 | 94 | 0.09504 | 0.07756 | TIE |
| deepseek | MB-2005 | mae | 162 | 1.512 | 1.778 | 73 | 68 | 21 | 0 | 5.987e-07 | 1.62e-06 | WIN |
| deepseek | MB-2006 | mae | 162 | 4.698 | 3.994 | 26 | 74 | 56 | 6 | 0.1357 | 0.005962 | LOSS |
| google | MB-2001 | accuracy | 166 | 0.4036 | 0.3554 | 3 | 64 | 56 | 43 | 0.523 | 0.4652 | TIE |
| google | MB-2002 | accuracy | 156 | 0.1859 | 0.1667 | 0 | 29 | 26 | 101 | 0.7877 | 0.6858 | TIE |
| google | MB-2003 | accuracy | 8 | 0.25 | 0 | 0 | 2 | 0 | 6 | 0.5 |  | TIE |
| meta-llama | MB-2001 | accuracy | 168 | 0.4048 | 0.1905 | 10 | 58 | 22 | 78 | 7.011e-05 | 5.699e-05 | WIN |
| meta-llama | MB-2002 | accuracy | 168 | 0.1964 | 0.1488 | 15 | 18 | 10 | 125 | 0.1849 | 0.1306 | TIE |
| meta-llama | MB-2003 | accuracy | 10 | 0.6 | 0 | 0 | 6 | 0 | 4 | 0.03125 | 0.03125 | WIN |
| meta-llama | MB-2005 | mae | 168 | 1.524 | 1.529 | 47 | 54 | 55 | 12 | 1 | 1 | TIE |
| meta-llama | MB-2006 | mae | 167 | 4.731 | 2400 | 20 | 82 | 56 | 9 | 0.03295 | 1.095e-05 | WIN |
| nvidia | MB-2001 | accuracy | 168 | 0.4048 | 0.6607 | 68 | 0 | 43 | 57 | 2.274e-13 | 5.474e-11 | LOSS |
| nvidia | MB-2002 | accuracy | 168 | 0.1964 | 0.2738 | 11 | 22 | 35 | 100 | 0.1112 | 0.08509 | TIE |
| nvidia | MB-2003 | accuracy | 258 | 0.469 | 0.5 | 28 | 93 | 101 | 36 | 0.6154 | 0.5657 | TIE |
| nvidia | MB-2005 | mae | 168 | 1.524 | 2.024 | 62 | 82 | 24 | 0 | 1.337e-08 | 3.402e-06 | WIN |
| nvidia | MB-2006 | mae | 167 | 4.731 | 3.814 | 41 | 83 | 43 | 0 | 0.0004639 | 0.2911 | TIE |
| openai | MB-2001 | accuracy | 168 | 0.4048 | 0.6607 | 68 | 0 | 43 | 57 | 2.274e-13 | 5.474e-11 | LOSS |
| openai | MB-2002 | accuracy | 168 | 0.1964 | 0.1905 | 16 | 17 | 16 | 119 | 1 | 0.8618 | TIE |
| openai | MB-2003 | accuracy | 10 | 0.6 | 0 | 0 | 6 | 0 | 4 | 0.03125 | 0.03125 | WIN |
| openai | MB-2005 | mae | 168 | 1.524 | 1.804 | 81 | 69 | 18 | 0 | 3.322e-08 | 1.361e-07 | WIN |
| openai | MB-2006 | mae | 167 | 4.731 | 4.251 | 68 | 76 | 23 | 0 | 8.534e-08 | 2.502e-07 | LOSS |
| openai | MB-2001 | accuracy | 168 | 0.4048 | 0.2143 | 19 | 49 | 17 | 83 | 0.0001015 | 8.185e-05 | WIN |
| openai | MB-2002 | accuracy | 168 | 0.1964 | 0.1845 | 12 | 21 | 19 | 116 | 0.8746 | 0.7518 | TIE |
| openai | MB-2003 | accuracy | 10 | 0.6 | 0 | 0 | 6 | 0 | 4 | 0.03125 | 0.03125 | WIN |
| openai | MB-2005 | mae | 168 | 1.524 | 2628 | 50 | 63 | 44 | 11 | 0.08135 | 0.004391 | WIN |
| openai | MB-2006 | mae | 167 | 4.731 | 4.157 | 32 | 81 | 53 | 1 | 0.01934 | 4.607e-05 | LOSS |
| qwen | MB-2001 | accuracy | 168 | 0.4048 | 0.6607 | 68 | 0 | 43 | 57 | 2.274e-13 | 5.474e-11 | LOSS |
| qwen | MB-2002 | accuracy | 168 | 0.1964 | 0.1667 | 15 | 18 | 13 | 122 | 0.4731 | 0.3692 | TIE |
| qwen | MB-2003 | accuracy | 10 | 0.6 | 0 | 0 | 6 | 0 | 4 | 0.03125 | 0.03125 | WIN |
| qwen | MB-2005 | mae | 168 | 1.524 | 1.613 | 81 | 53 | 34 | 0 | 0.053 | 0.05778 | TIE |
| qwen | MB-2006 | mae | 167 | 4.731 | 4.12 | 111 | 48 | 8 | 0 | 4.688e-08 | 1.434e-05 | LOSS |
| qwen | MB-2001 | accuracy | 87 | 0.4713 | 0.2644 | 10 | 31 | 13 | 33 | 0.00956 | 0.006656 | WIN |
