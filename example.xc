/* xcc YOUR_BOARD.xc example.xc -fxscope
 * xrun --xscope-port localhost:6363 a.xe
 * python xvu.py -n -w out.wav
 */
#include <xs1.h>
#include <xscope.h>

int main(void)
{
  int sinewave[48] = {
    0,
    2189866,
    4342263,
    6420363,
    8388608,
    10213322,
    11863283,
    13310260,
    14529495,
    15500126,
    16205546,
    16633685,
    16777216,
    16633685,
    16205546,
    15500126,
    14529495,
    13310260,
    11863283,
    10213322,
    8388608,
    6420363,
    4342263,
    2189866,
    0,
    -2189866,
    -4342263,
    -6420363,
    -8388608,
    -10213322,
    -11863283,
    -13310260,
    -14529495,
    -15500126,
    -16205546,
    -16633685,
    -16777216,
    -16633685,
    -16205546,
    -15500126,
    -14529495,
    -13310260,
    -11863283,
    -10213322,
    -8388608,
    -6420363,
    -4342263,
    -2189866,
  };
  int i, j = 0;
  for (j = 0; j < 48; j++) {
    sinewave[j] *= 32;
  }
  xscope_register(2,
    XSCOPE_CONTINUOUS, "P0", XSCOPE_INT, "-",
    XSCOPE_CONTINUOUS, "P1", XSCOPE_INT, "-"
  );
  j = 0;
  for (i = 0; i < 16000; i++) {
    xscope_int(0, sinewave[j]);
    xscope_int(1, sinewave[j] << 1);
    j++;
    if (j == 48)
      j = 0;
  }
  return 0;
}
