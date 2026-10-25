#ifndef ABAQUS_RANDOM29_H
#define ABAQUS_RANDOM29_H

/* Menu-only random stream. Bytes 0/1 hold the PRNG, 2/3 count menu samples;
 * the other four reserved bytes stay unused. No combat RNG or actor state. */
#define RANDOM29_SEED (*(u16 *)&v29RandomState[0])
#define RANDOM29_CLOCK (*(u16 *)&v29RandomState[2])

void random29Tick(void) {
    if(screen>ARENA)return;
    RANDOM29_CLOCK++;
}

u8 random29Pick(u8 count) {
    u8 sample;
    /* Addition is a permutation of the 16-bit state. User timing changes
     * this stream even when every visit begins on the same roster slot. */
    RANDOM29_SEED+=RANDOM29_CLOCK+frame;
    do {
        /* Full-period 16-bit LCG, independent of rng()/randomseed. The top
         * byte avoids the short low-bit patterns of repeated small picks. */
        RANDOM29_SEED=RANDOM29_SEED*109+89;
        sample=RANDOM29_SEED>>8;
        /* 252 is divisible by both 12 and 3: reject the remainder instead
         * of giving the first four fighters/first arena an extra outcome. */
    } while(sample>=252);
    return sample%count;
}

#endif
