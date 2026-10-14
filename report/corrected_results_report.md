# Corrected experiment results

NEQR-Gradient is a hybrid NEQR reconstruction followed by a classical forward gradient.
QHED uses four circuits with the stated shots per circuit. Historical outputs are in results/tables.
Trial standard deviations measure sampling variation, not uncertainty over independent source images.

## exp9 resource scaling

Rows: 10

| method | size | circuit_pass | n_qubits | circuit_depth | cx_count | u_count | circuits_per_trial | basis |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| QPIE-QHED | 4 | horizontal_0 | 4 | 26 | 11 | 16 | 4 | u,cx |
| QPIE-QHED | 4 | horizontal_1 | 4 | 28 | 12 | 17 | 4 | u,cx |
| QPIE-QHED | 4 | vertical_0 | 4 | 26 | 11 | 16 | 4 | u,cx |
| QPIE-QHED | 4 | vertical_1 | 4 | 28 | 12 | 17 | 4 | u,cx |
| NEQR-Gradient | 4 | hybrid_reconstruction | 8 | 1250 | 661 | 840 | 1 | u,cx |
| QPIE-QHED | 8 | horizontal_0 | 6 | 118 | 57 | 64 | 4 | u,cx |
| QPIE-QHED | 8 | horizontal_1 | 6 | 128 | 62 | 72 | 4 | u,cx |
| QPIE-QHED | 8 | vertical_0 | 6 | 118 | 57 | 64 | 4 | u,cx |
| QPIE-QHED | 8 | vertical_1 | 6 | 128 | 62 | 72 | 4 | u,cx |
| NEQR-Gradient | 8 | hybrid_reconstruction | 10 | 10492 | 6021 | 7853 | 1 | u,cx |

## negative patch check

Rows: 238

| Method | Size | Rim-free patches | Mean false positive pixel fraction |
| --- | --- | ---: | ---: |
| Sobel | 8 | 20 | 0.3781 |
| Canny | 8 | 20 | 0.0414 |
| Robinson | 8 | 20 | 0.3672 |
| Forward-Gradient | 8 | 20 | 0.5164 |
| Quantized-Gradient | 8 | 20 | 0.2203 |
| QPIE-QHED | 8 | 20 | 0.2573 |
| NEQR-Gradient | 8 | 20 | 0.2203 |
| Sobel | 16 | 14 | 0.3170 |
| Canny | 16 | 14 | 0.0458 |
| Robinson | 16 | 14 | 0.3186 |
| Forward-Gradient | 16 | 14 | 0.5257 |
| Quantized-Gradient | 16 | 14 | 0.2433 |
| QPIE-QHED | 16 | 14 | 0.1216 |
| NEQR-Gradient | 16 | 14 | 0.2433 |

## timing analysis

Rows: 10

| method | mean_time_ms | std_time_ms | min_time_ms | max_time_ms | size |
| --- | --- | --- | --- | --- | --- |
| Sobel | 0.0220 | 0.0079 | 0.0168 | 0.0377 | 4 |
| Canny | 0.0308 | 0.0074 | 0.0235 | 0.0448 | 4 |
| Robinson | 0.0501 | 0.0070 | 0.0434 | 0.0608 | 4 |
| QPIE-QHED | 531.2881 | 14.4392 | 513.1379 | 547.2125 | 4 |
| NEQR-Gradient | 137.1323 | 10.0740 | 127.5693 | 156.4075 | 4 |
| Sobel | 0.0307 | 0.0013 | 0.0288 | 0.0323 | 8 |
| Canny | 0.1184 | 0.0241 | 0.0916 | 0.1539 | 8 |
| Robinson | 0.0865 | 0.0050 | 0.0827 | 0.0962 | 8 |
| QPIE-QHED | 577.6690 | 38.0308 | 539.4127 | 649.2411 | 8 |
| NEQR-Gradient | 156.1276 | 7.5019 | 144.6999 | 167.3507 | 8 |

## validation benchmark

Rows: 224

| Dataset | Method | Size | Entries | Mean exact F1 |
| --- | --- | --- | ---: | ---: |
| synthetic | Sobel | 8 | 8 | 0.8737 |
| synthetic | Canny | 8 | 8 | 0.6861 |
| synthetic | Robinson | 8 | 8 | 0.8663 |
| synthetic | Forward-Gradient | 8 | 8 | 0.6760 |
| synthetic | Quantized-Gradient | 8 | 8 | 0.6760 |
| synthetic | QPIE-QHED | 8 | 8 | 0.4522 |
| synthetic | NEQR-Gradient | 8 | 8 | 0.6760 |
| lunar | Sobel | 16 | 15 | 0.2612 |
| lunar | Canny | 16 | 15 | 0.0976 |
| lunar | Robinson | 16 | 15 | 0.2598 |
| lunar | Forward-Gradient | 16 | 15 | 0.2832 |
| lunar | Quantized-Gradient | 16 | 15 | 0.2139 |
| lunar | QPIE-QHED | 16 | 15 | 0.1287 |
| lunar | NEQR-Gradient | 16 | 15 | 0.2139 |
| lunar | Sobel | 8 | 9 | 0.3234 |
| lunar | Canny | 8 | 9 | 0.0661 |
| lunar | Robinson | 8 | 9 | 0.3224 |
| lunar | Forward-Gradient | 8 | 9 | 0.3668 |
| lunar | Quantized-Gradient | 8 | 9 | 0.2931 |
| lunar | QPIE-QHED | 8 | 9 | 0.2610 |
| lunar | NEQR-Gradient | 8 | 9 | 0.2931 |
