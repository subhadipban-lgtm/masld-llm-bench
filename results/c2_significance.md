# C2 paired significance (McNemar exact + Wilcoxon signed-rank)

Verdicts at p < 0.05: accuracy -> McNemar, MAE -> Wilcoxon (better = lower).

## Candidate: qwen3-0.6b-masld (`qwen3-0.6b-masld__MB-20xx_PAIRED.jsonl.gz`)

57 comparisons — WIN 18 / LOSS 11 / TIE 28

| reference | task | metric | n | cand | ref | both | cand_only | ref_only | neither | mcnemar_p | wilcoxon_p | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| amazon__nova-pro-v1 | MB-2001 | accuracy | 168 | 0.4048 | 0.1667 | 9 | 59 | 19 | 81 | 6.415e-06 | 5.923e-06 | WIN |
| amazon__nova-pro-v1 | MB-2002 | accuracy | 168 | 0.1964 | 0.1726 | 13 | 20 | 16 | 119 | 0.6177 | 0.505 | TIE |
| amazon__nova-pro-v1 | MB-2003 | accuracy | 10 | 0.6 | 0.2 | 0 | 6 | 2 | 2 | 0.2891 | 0.2891 | TIE |
| amazon__nova-pro-v1 | MB-2005 | mae | 168 | 1.524 | 6547 | 41 | 83 | 44 | 0 | 0.0006846 | 0.0002361 | WIN |
| amazon__nova-pro-v1 | MB-2006 | mae | 167 | 4.731 | 9237 | 33 | 68 | 55 | 11 | 0.2792 | 0.002212 | WIN |
| anthropic__claude-sonnet-4.5 | MB-2001 | accuracy | 168 | 0.4048 | 0.04762 | 0 | 68 | 8 | 92 | 5.633e-13 | 5.882e-12 | WIN |
| anthropic__claude-sonnet-4.5 | MB-2002 | accuracy | 168 | 0.1964 | 0.005952 | 0 | 33 | 1 | 134 | 4.075e-09 | 4.066e-08 | WIN |
| anthropic__claude-sonnet-4.5 | MB-2003 | accuracy | 10 | 0.6 | 0.6 | 4 | 2 | 2 | 2 | 1 | 1 | TIE |
| anthropic__claude-sonnet-4.5 | MB-2005 | mae | 168 | 1.524 | 2.892e+04 | 17 | 75 | 76 | 0 | 1 | 0.2919 | TIE |
| anthropic__claude-sonnet-4.5 | MB-2006 | mae | 167 | 4.731 | 3.886 | 47 | 64 | 56 | 0 | 0.523 | 0.0872 | TIE |
| deepseek__deepseek-chat | MB-2001 | accuracy | 163 | 0.3988 | 0.6319 | 56 | 9 | 47 | 51 | 2.572e-07 | 3.815e-07 | LOSS |
| deepseek__deepseek-chat | MB-2002 | accuracy | 163 | 0.1902 | 0.1718 | 14 | 17 | 14 | 118 | 0.7201 | 0.59 | TIE |
| deepseek__deepseek-chat | MB-2003 | accuracy | 258 | 0.469 | 0.4186 | 64 | 57 | 44 | 93 | 0.2323 | 0.1958 | TIE |
| deepseek__deepseek-chat | MB-2005 | mae | 162 | 1.512 | 1.778 | 73 | 68 | 21 | 0 | 5.987e-07 | 1.62e-06 | WIN |
| deepseek__deepseek-chat | MB-2006 | mae | 162 | 4.698 | 3.994 | 26 | 74 | 56 | 6 | 0.1357 | 0.005962 | LOSS |
| google__gemini-2.5-pro | MB-2001 | accuracy | 168 | 0.4048 | 0.3631 | 3 | 65 | 58 | 42 | 0.5887 | 0.5279 | TIE |
| google__gemini-2.5-pro | MB-2002 | accuracy | 168 | 0.1964 | 0.1548 | 0 | 33 | 26 | 109 | 0.435 | 0.3621 | TIE |
| google__gemini-2.5-pro | MB-2003 | accuracy | 124 | 0.4194 | 0.008065 | 0 | 52 | 1 | 71 | 1.199e-14 | 2.463e-12 | WIN |
| meta-llama__llama-3.3-70b-instruct | MB-2001 | accuracy | 168 | 0.4048 | 0.1905 | 10 | 58 | 22 | 78 | 7.011e-05 | 5.699e-05 | WIN |
| meta-llama__llama-3.3-70b-instruct | MB-2002 | accuracy | 168 | 0.1964 | 0.1488 | 15 | 18 | 10 | 125 | 0.1849 | 0.1306 | TIE |
| meta-llama__llama-3.3-70b-instruct | MB-2003 | accuracy | 10 | 0.6 | 0.1 | 1 | 5 | 0 | 4 | 0.0625 | 0.0625 | TIE |
| meta-llama__llama-3.3-70b-instruct | MB-2005 | mae | 168 | 1.524 | 1.529 | 47 | 54 | 55 | 12 | 1 | 1 | TIE |
| meta-llama__llama-3.3-70b-instruct | MB-2006 | mae | 167 | 4.731 | 2400 | 20 | 82 | 56 | 9 | 0.03295 | 1.095e-05 | WIN |
| nvidia__nemotron-3-super-120b-a12b:free | MB-2001 | accuracy | 168 | 0.4048 | 0.6607 | 68 | 0 | 43 | 57 | 2.274e-13 | 5.474e-11 | LOSS |
| nvidia__nemotron-3-super-120b-a12b:free | MB-2002 | accuracy | 168 | 0.1964 | 0.2738 | 11 | 22 | 35 | 100 | 0.1112 | 0.08509 | TIE |
| nvidia__nemotron-3-super-120b-a12b:free | MB-2003 | accuracy | 258 | 0.469 | 0.5 | 28 | 93 | 101 | 36 | 0.6154 | 0.5657 | TIE |
| nvidia__nemotron-3-super-120b-a12b:free | MB-2005 | mae | 168 | 1.524 | 2.024 | 62 | 82 | 24 | 0 | 1.337e-08 | 3.402e-06 | WIN |
| nvidia__nemotron-3-super-120b-a12b:free | MB-2006 | mae | 167 | 4.731 | 3.814 | 41 | 83 | 43 | 0 | 0.0004639 | 0.2911 | TIE |
| openai__gpt-4.1-mini | MB-2001 | accuracy | 168 | 0.4048 | 0.6607 | 68 | 0 | 43 | 57 | 2.274e-13 | 5.474e-11 | LOSS |
| openai__gpt-4.1-mini | MB-2002 | accuracy | 168 | 0.1964 | 0.1905 | 16 | 17 | 16 | 119 | 1 | 0.8618 | TIE |
| openai__gpt-4.1-mini | MB-2003 | accuracy | 10 | 0.6 | 0.5 | 5 | 1 | 0 | 4 | 1 |  | TIE |
| openai__gpt-4.1-mini | MB-2005 | mae | 168 | 1.524 | 1.804 | 81 | 69 | 18 | 0 | 3.322e-08 | 1.361e-07 | WIN |
| openai__gpt-4.1-mini | MB-2006 | mae | 167 | 4.731 | 4.251 | 68 | 76 | 23 | 0 | 8.534e-08 | 2.502e-07 | LOSS |
| openai__gpt-4.1 | MB-2001 | accuracy | 168 | 0.4048 | 0.5774 | 57 | 11 | 40 | 60 | 5.704e-05 | 4.89e-05 | LOSS |
| openai__gpt-4.1 | MB-2002 | accuracy | 168 | 0.1964 | 0.1905 | 16 | 17 | 16 | 119 | 1 | 0.8618 | TIE |
| openai__gpt-4.1 | MB-2003 | accuracy | 10 | 0.6 | 0.3 | 3 | 3 | 0 | 4 | 0.25 | 0.25 | TIE |
| openai__gpt-4.1 | MB-2005 | mae | 168 | 1.524 | 1.815 | 83 | 69 | 16 | 0 | 5.24e-09 | 2.97e-08 | WIN |
| openai__gpt-4.1 | MB-2006 | mae | 167 | 4.731 | 4.102 | 28 | 82 | 57 | 0 | 0.0414 | 0.002673 | LOSS |
| openai__gpt-4o-mini | MB-2001 | accuracy | 168 | 0.4048 | 0.5179 | 49 | 19 | 38 | 62 | 0.01635 | 0.01185 | LOSS |
| openai__gpt-4o-mini | MB-2002 | accuracy | 168 | 0.1964 | 0.1845 | 12 | 21 | 19 | 116 | 0.8746 | 0.7518 | TIE |
| openai__gpt-4o-mini | MB-2003 | accuracy | 10 | 0.6 | 0.4 | 3 | 3 | 1 | 3 | 0.625 | 0.625 | TIE |
| openai__gpt-4o-mini | MB-2005 | mae | 168 | 1.524 | 2628 | 50 | 63 | 44 | 11 | 0.08135 | 0.004391 | WIN |
| openai__gpt-4o-mini | MB-2006 | mae | 167 | 4.731 | 4.157 | 32 | 81 | 53 | 1 | 0.01934 | 4.607e-05 | LOSS |
| openai__gpt-5.6-luna | MB-2001 | accuracy | 168 | 0.4048 | 0.07143 | 5 | 63 | 7 | 93 | 2.275e-12 | 2.182e-11 | WIN |
| openai__gpt-5.6-luna | MB-2002 | accuracy | 168 | 0.1964 | 0 | 0 | 33 | 0 | 135 | 2.328e-10 | 9.216e-09 | WIN |
| openai__gpt-5.6-luna | MB-2003 | accuracy | 10 | 0.6 | 0.5 | 3 | 3 | 2 | 2 | 1 | 1 | TIE |
| openai__gpt-5.6-luna | MB-2005 | mae | 168 | 1.524 | 1.714 | 4 | 10 | 7 | 147 | 0.6291 |  | TIE |
| qwen__qwen-2.5-72b-instruct | MB-2001 | accuracy | 168 | 0.4048 | 0.6607 | 68 | 0 | 43 | 57 | 2.274e-13 | 5.474e-11 | LOSS |
| qwen__qwen-2.5-72b-instruct | MB-2002 | accuracy | 168 | 0.1964 | 0.1667 | 15 | 18 | 13 | 122 | 0.4731 | 0.3692 | TIE |
| qwen__qwen-2.5-72b-instruct | MB-2003 | accuracy | 10 | 0.6 | 0.3 | 2 | 4 | 1 | 3 | 0.375 | 0.375 | TIE |
| qwen__qwen-2.5-72b-instruct | MB-2005 | mae | 168 | 1.524 | 1.613 | 81 | 53 | 34 | 0 | 0.053 | 0.05778 | TIE |
| qwen__qwen-2.5-72b-instruct | MB-2006 | mae | 167 | 4.731 | 4.12 | 111 | 48 | 8 | 0 | 4.688e-08 | 1.434e-05 | LOSS |
| qwen__qwen3-235b-a22b-2507 | MB-2001 | accuracy | 168 | 0.4048 | 0.4702 | 17 | 51 | 62 | 38 | 0.3469 | 0.3008 | TIE |
| qwen__qwen3-235b-a22b-2507 | MB-2002 | accuracy | 168 | 0.1964 | 0.1786 | 10 | 23 | 20 | 115 | 0.7608 | 0.6473 | TIE |
| qwen__qwen3-235b-a22b-2507 | MB-2003 | accuracy | 10 | 0.6 | 0 | 0 | 6 | 0 | 4 | 0.03125 | 0.03125 | WIN |
| qwen__qwen3-235b-a22b-2507 | MB-2005 | mae | 168 | 1.524 | 13.78 | 65 | 77 | 26 | 0 | 4.945e-07 | 4.302e-05 | WIN |
| qwen__qwen3-235b-a22b-2507 | MB-2006 | mae | 167 | 4.731 | 27.85 | 67 | 56 | 44 | 0 | 0.2713 | 0.01148 | WIN |

## Candidate: qwen3-1.7b-masld (`qwen3-1.7b-masld__MB-20xx_PAIRED.jsonl.gz`)

57 comparisons — WIN 34 / LOSS 0 / TIE 23

| reference | task | metric | n | cand | ref | both | cand_only | ref_only | neither | mcnemar_p | wilcoxon_p | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| amazon__nova-pro-v1 | MB-2001 | accuracy | 168 | 0.6548 | 0.1667 | 26 | 84 | 2 | 56 | 9.673e-23 | 9.378e-19 | WIN |
| amazon__nova-pro-v1 | MB-2002 | accuracy | 168 | 0.1845 | 0.1726 | 10 | 21 | 19 | 118 | 0.8746 | 0.7518 | TIE |
| amazon__nova-pro-v1 | MB-2003 | accuracy | 10 | 0.8 | 0.2 | 2 | 6 | 0 | 2 | 0.03125 | 0.03125 | WIN |
| amazon__nova-pro-v1 | MB-2005 | mae | 168 | 1.375 | 6547 | 39 | 87 | 42 | 0 | 9.207e-05 | 9.486e-06 | WIN |
| amazon__nova-pro-v1 | MB-2006 | mae | 167 | 2.162 | 9237 | 24 | 109 | 23 | 11 | 1.387e-14 | 2.874e-15 | WIN |
| anthropic__claude-sonnet-4.5 | MB-2001 | accuracy | 168 | 0.6548 | 0.04762 | 6 | 104 | 2 | 56 | 1.398e-28 | 3.877e-23 | WIN |
| anthropic__claude-sonnet-4.5 | MB-2002 | accuracy | 168 | 0.1845 | 0.005952 | 0 | 31 | 1 | 136 | 1.537e-08 | 1.137e-07 | WIN |
| anthropic__claude-sonnet-4.5 | MB-2003 | accuracy | 10 | 0.8 | 0.6 | 6 | 2 | 0 | 2 | 0.5 |  | TIE |
| anthropic__claude-sonnet-4.5 | MB-2005 | mae | 168 | 1.375 | 2.892e+04 | 15 | 76 | 77 | 0 | 1 | 0.101 | TIE |
| anthropic__claude-sonnet-4.5 | MB-2006 | mae | 167 | 2.162 | 3.886 | 18 | 119 | 30 | 0 | 9.583e-14 | 2.446e-16 | WIN |
| deepseek__deepseek-chat | MB-2001 | accuracy | 163 | 0.6503 | 0.6319 | 94 | 12 | 9 | 48 | 0.6636 | 0.5127 | TIE |
| deepseek__deepseek-chat | MB-2002 | accuracy | 163 | 0.184 | 0.1718 | 12 | 18 | 16 | 117 | 0.8642 | 0.7316 | TIE |
| deepseek__deepseek-chat | MB-2003 | accuracy | 258 | 0.5155 | 0.4186 | 50 | 83 | 58 | 67 | 0.04288 | 0.03526 | WIN |
| deepseek__deepseek-chat | MB-2005 | mae | 162 | 1.389 | 1.778 | 57 | 77 | 28 | 0 | 1.853e-06 | 1.446e-06 | WIN |
| deepseek__deepseek-chat | MB-2006 | mae | 162 | 2.13 | 3.994 | 16 | 120 | 20 | 6 | 1.419e-18 | 3.587e-17 | WIN |
| google__gemini-2.5-pro | MB-2001 | accuracy | 168 | 0.6548 | 0.3631 | 11 | 99 | 50 | 8 | 7.328e-05 | 5.964e-05 | WIN |
| google__gemini-2.5-pro | MB-2002 | accuracy | 168 | 0.1845 | 0.1548 | 2 | 29 | 24 | 113 | 0.5831 | 0.4922 | TIE |
| google__gemini-2.5-pro | MB-2003 | accuracy | 124 | 0.5323 | 0.008065 | 1 | 65 | 0 | 58 | 5.421e-20 | 7.49e-16 | WIN |
| meta-llama__llama-3.3-70b-instruct | MB-2001 | accuracy | 168 | 0.6548 | 0.1905 | 31 | 79 | 1 | 57 | 1.34e-22 | 2.766e-18 | WIN |
| meta-llama__llama-3.3-70b-instruct | MB-2002 | accuracy | 168 | 0.1845 | 0.1488 | 13 | 18 | 12 | 125 | 0.3616 | 0.2733 | TIE |
| meta-llama__llama-3.3-70b-instruct | MB-2003 | accuracy | 10 | 0.8 | 0.1 | 1 | 7 | 0 | 2 | 0.01562 | 0.01562 | WIN |
| meta-llama__llama-3.3-70b-instruct | MB-2005 | mae | 168 | 1.375 | 1.529 | 53 | 53 | 50 | 12 | 0.8439 | 0.04179 | WIN |
| meta-llama__llama-3.3-70b-instruct | MB-2006 | mae | 167 | 2.162 | 2400 | 15 | 115 | 28 | 9 | 1.018e-13 | 6.382e-18 | WIN |
| nvidia__nemotron-3-super-120b-a12b:free | MB-2001 | accuracy | 168 | 0.6548 | 0.6607 | 106 | 4 | 5 | 53 | 1 | 1 | TIE |
| nvidia__nemotron-3-super-120b-a12b:free | MB-2002 | accuracy | 168 | 0.1845 | 0.2738 | 5 | 26 | 41 | 96 | 0.08644 | 0.06687 | TIE |
| nvidia__nemotron-3-super-120b-a12b:free | MB-2003 | accuracy | 258 | 0.5155 | 0.5 | 79 | 54 | 50 | 75 | 0.7688 | 0.6949 | TIE |
| nvidia__nemotron-3-super-120b-a12b:free | MB-2005 | mae | 168 | 1.375 | 2.024 | 52 | 94 | 22 | 0 | 8.656e-12 | 3.837e-09 | WIN |
| nvidia__nemotron-3-super-120b-a12b:free | MB-2006 | mae | 167 | 2.162 | 3.814 | 18 | 116 | 33 | 0 | 5.018e-12 | 6.391e-13 | WIN |
| openai__gpt-4.1-mini | MB-2001 | accuracy | 168 | 0.6548 | 0.6607 | 106 | 4 | 5 | 53 | 1 | 1 | TIE |
| openai__gpt-4.1-mini | MB-2002 | accuracy | 168 | 0.1845 | 0.1905 | 15 | 16 | 17 | 120 | 1 | 0.8618 | TIE |
| openai__gpt-4.1-mini | MB-2003 | accuracy | 10 | 0.8 | 0.5 | 4 | 4 | 1 | 1 | 0.375 | 0.375 | TIE |
| openai__gpt-4.1-mini | MB-2005 | mae | 168 | 1.375 | 1.804 | 58 | 83 | 27 | 0 | 8.31e-08 | 1.008e-07 | WIN |
| openai__gpt-4.1-mini | MB-2006 | mae | 167 | 2.162 | 4.251 | 17 | 133 | 17 | 0 | 1.731e-23 | 1.58e-20 | WIN |
| openai__gpt-4.1 | MB-2001 | accuracy | 168 | 0.6548 | 0.5774 | 93 | 17 | 4 | 54 | 0.007197 | 0.004556 | WIN |
| openai__gpt-4.1 | MB-2002 | accuracy | 168 | 0.1845 | 0.1905 | 15 | 16 | 17 | 120 | 1 | 0.8618 | TIE |
| openai__gpt-4.1 | MB-2003 | accuracy | 10 | 0.8 | 0.3 | 3 | 5 | 0 | 2 | 0.0625 | 0.0625 | TIE |
| openai__gpt-4.1 | MB-2005 | mae | 168 | 1.375 | 1.815 | 58 | 84 | 26 | 0 | 2.614e-08 | 4.222e-08 | WIN |
| openai__gpt-4.1 | MB-2006 | mae | 167 | 2.162 | 4.102 | 24 | 125 | 18 | 0 | 6.68e-21 | 1.087e-18 | WIN |
| openai__gpt-4o-mini | MB-2001 | accuracy | 168 | 0.6548 | 0.5179 | 85 | 25 | 2 | 56 | 5.648e-06 | 9.584e-06 | WIN |
| openai__gpt-4o-mini | MB-2002 | accuracy | 168 | 0.1845 | 0.1845 | 14 | 17 | 17 | 120 | 1 | 1 | TIE |
| openai__gpt-4o-mini | MB-2003 | accuracy | 10 | 0.8 | 0.4 | 3 | 5 | 1 | 1 | 0.2188 | 0.2188 | TIE |
| openai__gpt-4o-mini | MB-2005 | mae | 168 | 1.375 | 2628 | 48 | 65 | 44 | 11 | 0.05491 | 0.0003638 | WIN |
| openai__gpt-4o-mini | MB-2006 | mae | 167 | 2.162 | 4.157 | 22 | 120 | 24 | 1 | 1.492e-16 | 1.927e-19 | WIN |
| openai__gpt-5.6-luna | MB-2001 | accuracy | 168 | 0.6548 | 0.07143 | 12 | 98 | 0 | 58 | 6.311e-30 | 4.184e-23 | WIN |
| openai__gpt-5.6-luna | MB-2002 | accuracy | 168 | 0.1845 | 0 | 0 | 31 | 0 | 137 | 9.313e-10 | 2.58e-08 | WIN |
| openai__gpt-5.6-luna | MB-2003 | accuracy | 10 | 0.8 | 0.5 | 5 | 3 | 0 | 2 | 0.25 | 0.25 | TIE |
| openai__gpt-5.6-luna | MB-2005 | mae | 168 | 1.375 | 1.714 | 5 | 9 | 7 | 147 | 0.8036 | 0.3438 | TIE |
| qwen__qwen-2.5-72b-instruct | MB-2001 | accuracy | 168 | 0.6548 | 0.6607 | 106 | 4 | 5 | 53 | 1 | 1 | TIE |
| qwen__qwen-2.5-72b-instruct | MB-2002 | accuracy | 168 | 0.1845 | 0.1667 | 15 | 16 | 13 | 124 | 0.7111 | 0.5775 | TIE |
| qwen__qwen-2.5-72b-instruct | MB-2003 | accuracy | 10 | 0.8 | 0.3 | 3 | 5 | 0 | 2 | 0.0625 | 0.0625 | TIE |
| qwen__qwen-2.5-72b-instruct | MB-2005 | mae | 168 | 1.375 | 1.613 | 50 | 73 | 45 | 0 | 0.0126 | 0.003644 | WIN |
| qwen__qwen-2.5-72b-instruct | MB-2006 | mae | 167 | 2.162 | 4.12 | 19 | 128 | 20 | 0 | 1.804e-20 | 2.524e-18 | WIN |
| qwen__qwen3-235b-a22b-2507 | MB-2001 | accuracy | 168 | 0.6548 | 0.4702 | 35 | 75 | 44 | 14 | 0.005727 | 0.004486 | WIN |
| qwen__qwen3-235b-a22b-2507 | MB-2002 | accuracy | 168 | 0.1845 | 0.1786 | 10 | 21 | 20 | 117 | 1 | 0.8759 | TIE |
| qwen__qwen3-235b-a22b-2507 | MB-2003 | accuracy | 10 | 0.8 | 0 | 0 | 8 | 0 | 2 | 0.007812 | 0.007812 | WIN |
| qwen__qwen3-235b-a22b-2507 | MB-2005 | mae | 168 | 1.375 | 13.78 | 55 | 84 | 29 | 0 | 2.201e-07 | 9.323e-07 | WIN |
| qwen__qwen3-235b-a22b-2507 | MB-2006 | mae | 167 | 2.162 | 27.85 | 22 | 121 | 24 | 0 | 8.92e-17 | 9.875e-17 | WIN |
