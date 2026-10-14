# FRQI live variant

FRQI uses eight position qubits plus one brightness-angle qubit. For pixel i, theta_i = (pi/2) I_i/255; the state is a uniform superposition over positions with color state cos(theta_i)|0> + sin(theta_i)|1>. Position-register Hadamard interference produces the color-marginal probability p = (1 - cos(theta_a-theta_b))/N. The runner reconstructs absolute intensity differences as (1020/pi) arcsin(sqrt(N p/2)). Sampling estimates are clipped to the physical intensity range before reconstruction.

The original QPIE system and its saved results are retained as historical baselines. All variant edge evidence is measured from actual Aer inference circuits. Four passes cover both axes and pair offsets. The state preparation is native Initialize in simulation, with primitive export available.

Validation: 32 unit tests and an end-to-end browser upload run pass. Each uploaded-image check executes 140 actual inference circuits and 1,146,880 shots.

Native lunar validation: all 512x512 pixels, 5,476 inference circuits, 44,859,392 shots, 86 checkpoint batches; all trace counts agree with the inference audit. Desktop and 360px mobile views have no script errors or horizontal overflow. Saved screenshots and the verification JSON are in the variant output directory.
