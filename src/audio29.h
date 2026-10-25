#ifndef ABAQUS_AUDIO29_H
#define ABAQUS_AUDIO29_H
/* Only v29AudioState is new mutable storage. Levels: 0 off, 1 low,
 * 2 medium, 3 high. Defaults favor contacts over the music bed.
 * [0..2] levels, [3] cursor, [4] boot stamp, [5..6] reserved,
 * [7] last effect volpan, [8] last slot, [9] last command kind.
 * [10] command serial (wraps), [11] sound-page return route,
 * [12] cached master music gain, [13] last audible music level. */
#define AUDIO29_PAGE 4
#define AUDIO29_MUSIC v29AudioState[0]
#define AUDIO29_EFFECTS v29AudioState[1]
#define AUDIO29_VOICE v29AudioState[2]
#define AUDIO29_CURSOR v29AudioState[3]
const u8 audio29MusicVolumes[4]={0,24,48,72};
const u8 audio29EffectGains[4]={0,5,10,14};

void audio29Init(void) {
    if(v29AudioState[4]==29)return;
    AUDIO29_MUSIC=2;AUDIO29_EFFECTS=3;AUDIO29_VOICE=3;
    AUDIO29_CURSOR=0;v29AudioState[4]=29;
    v29AudioState[8]=255;v29AudioState[12]=48;v29AudioState[13]=2;
}
#define AUDIO29_CUE_LEVEL(slot) (((slot)>=6 && (slot)<=8)?AUDIO29_VOICE:AUDIO29_EFFECTS)
u8 audio29Volpan(u8 slot) {
    u8 gain=audio29EffectGains[AUDIO29_CUE_LEVEL(slot)];
    /* Soft whiff and menu tick; dry impacts and speech retain full gain. */
    if(slot==0)gain=(gain+1)>>1;
    else if(slot==9)gain=(gain*3)>>2;
    return (gain<<4)|8;
}
#define AUDIO29_MUSIC_TARGET (musicOn?v29AudioState[12]:0)
#endif
