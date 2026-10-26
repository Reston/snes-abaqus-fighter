#ifndef ABAQUS_FIGHTER_PERSONALITY_H
#define ABAQUS_FIGHTER_PERSONALITY_H

/* Presentation only, included after the game globals/renderer declarations.
 * Approved 96x80 frames, original palettes, fixed actor origins. The existing
 * intro/roundEnd countdowns own every beat, so pause needs no extra clock or
 * mutable state. No action, physics, winner, duration or input is changed.
 * Intro settles before FIGHT; victory plays once and holds its final pose.
 * Names/design rationale live in docs/EXPANSION-04-FIGHTER-PERSONALITY.md.
 */
const u8 personalityIntroFrames[12][4]={
    {42,43,35,32}, /* Damian: Kernel salute */
    {40,28,40,43}, /* Ivo: Capital guard */
    {34, 6,35,32}, /* Cristobal: Atomic one-two */
    {28,44,45,35}, /* Cote: Balance check */
    {34,42,40,32}, /* Negger: Macro brace */
    {44,45,46,32}, /* David: Audit rise */
    {40,42,43,35}, /* Fernando: Legacy seal */
    {40,34,35,32}, /* Cristian: Risk reversal */
    {28,42,43,32}, /* Madariaga: Merge pulse */
    {42,43,45,32}, /* Reston: Cloud horizon */
    {35,45,46,32}, /* Roxana: Close-out flourish */
    {44,28,42,35}  /* Lars: Nordic stamp */
};
const u8 personalityVictoryFrames[12][7]={
    {43,42,45,46,11,46,11},
    {40,28,42,43,46,11,46},
    {34, 6,35,45,11,46,11},
    {28,44,45,35,46,11,46},
    {34,42,43,40,46,11,11},
    {44,45,13,45,46,11,46},
    {40,42,43,35,45,46,11},
    {40,34, 6,35,45,11,46},
    {28,42,43,35,46,11,46},
    {42,43,35,45,46,11,11},
    {35,45,46,11,46,45,11},
    {44,28,42,43,45,46,11}
};

u8 personalityIntroFrame(u8 id) {
    u8 tick,beat;
    if(id>=CHARACTER_COUNT)return 16;
    tick=110-intro;
    if(tick<8)return 16;
    if(tick>=56)return 32;
    if(tick<20)beat=0;
    else if(tick<32)beat=1;
    else if(tick<44)beat=2;
    else beat=3;
    return personalityIntroFrames[id][beat];
}

u8 personalityVictoryFrame(u8 id) {
    u8 tick,beat;
    if(id>=CHARACTER_COUNT)return 11;
    tick=180-roundEnd;
    if(tick<20)beat=0;
    else if(tick<40)beat=1;
    else if(tick<64)beat=2;
    else if(tick<88)beat=3;
    else if(tick<116)beat=4;
    else if(tick<144)beat=5;
    else beat=6;
    return personalityVictoryFrames[id][beat];
}

/* Borrow the ONE existing 16x16 impact slot only while it has no impact.
 * Intro gives each side its own twelve-tick accent; roundEnd uses the winner.
 * Existing resident tiles/palette 2: spark 384..390, orb 392..396,
 * hollow arc 416..418, heel crest 420..424. No VRAM or CGRAM transfers.
 * Distinct paths complement the gestures without making a gameplay wave.
 */
u8 personalityAccent(void) {
    Fighter *f;
    u8 p,tick,phase;
    u16 tile=384;
    s16 x,y,dx=24;
    if(roundEnd) {
        if(winner>=2)return 0;
        tick=180-roundEnd;
        if(tick<32)return 0;
        if(tick>=64 && tick<108)return 0;
        if(tick>=140)return 0;
        p=winner;
    } else if(intro) {
        tick=110-intro;
        if(tick<20)return 0;
        if(tick<32){p=0;tick-=20;}
        else if(tick<36)return 0;
        else if(tick<48){p=1;tick-=36;}
        else return 0;
    } else return 0;
    f=&fighters[p];phase=(tick>>2)&3;y=FLOOR-44;
    switch(f->id) {
    case 0:dx=18+(phase<<2);tile=392+(phase%3)*2;break;
    case 1:dx=30;y=FLOOR-42;tile=416+((phase&1)<<1);break;
    case 2:dx=24+(phase<<2);y=FLOOR-38;tile=384+(phase<<1);break;
    case 3:dx=22;y=FLOOR-26-(phase<<2);tile=416+((phase&1)<<1);break;
    case 4:dx=8;y=FLOOR-12;tile=420+(phase%3)*2;break;
    case 5:dx=18;y=FLOOR-40-(phase<<2);tile=384+(phase<<1);break;
    case 6:dx=(phase<<2)-8;y=FLOOR-12;tile=420+(phase%3)*2;break;
    case 7:dx=18+phase*3;y=FLOOR-38-phase*3;tile=384+(phase<<1);break;
    case 8:dx=26;y=FLOOR-12;tile=420+((phase&1)<<1);break;
    case 9:dx=30;y=FLOOR-40-(phase&1)*3;tile=396-(phase%3)*2;break;
    case 10:dx=14;y=FLOOR-48-phase*3;tile=416+((phase&1)<<1);break;
    case 11:dx=12+(phase<<2);y=FLOOR-12;tile=424-(phase%3)*2;break;
    default:return 0;
    }
    x=f->x>>4;
    if(f->face)x+=dx;else x-=dx;
    y+=f->y>>4;
    if(x<8)x=8;else if(x>248)x=248;
    if(y<8)y=8;else if(y>208)y=208;
    oamSet(OAM_EFFECT_BASE,x-8,y-8,3,f->face?0:1,0,tile,2);
    oamSetEx(OAM_EFFECT_BASE,1,OBJ_SHOW);
    return 1;
}

#endif
