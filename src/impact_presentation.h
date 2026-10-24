/* Impact-only feedback. Fighter/Wave, attack profiles and DMA stay unchanged.
 * fxType low bits retain legacy 0=strike, 1=guard; 2 uses spare light cells.
 * Its unused high bit latches direction. No new mutable RAM is necessary.
 * hurtWithRecoil receives the snapshotted action so trades classify correctly.
 */
#ifndef IMPACT_PRESENTATION_H
#define IMPACT_PRESENTATION_H
#define IMPACT_STRONG 0
#define IMPACT_GUARD 1
#define IMPACT_LIGHT 2
#define IMPACT_KIND_MASK 3
#define IMPACT_FACING 128

u8 beginImpact(u8 action,u8 blocked,u8 direction) {
    u8 kind,life,stop,kick;
    if(blocked) {
        kind=IMPACT_GUARD;life=8;stop=5;kick=0;
    } else if(action==1 || action==4) {
        kind=IMPACT_LIGHT;life=6;stop=7;kick=2;
    } else {
        kind=IMPACT_STRONG;life=10;stop=10;kick=6;
    }
    /* A weaker second contact in a trade must not shorten the strong hit or
     * replace its one spark/direction. Equal classes retain legacy last-hit
     * ownership. Damage and both hit reactions still resolve atomically. */
    if(hitstop>stop)return 0;
    fxType=kind;fxLife=life;hitstop=stop;shake=kick;
    if(direction)fxType|=IMPACT_FACING;
    return 1;
}

void drawImpact(void) {
    u8 phase;
    u16 tile;
    if(!fxLife){oamSetVisible(OAM_EFFECT_BASE,OBJ_HIDE);return;}
    if(animationAdvance)fxLife--;
    if((fxType&IMPACT_KIND_MASK)==IMPACT_GUARD)tile=fxLife>4?416:418;
    else if((fxType&IMPACT_KIND_MASK)==IMPACT_LIGHT)tile=fxLife>3?426:428;
    else {
        phase=(10-fxLife)>>1;if(phase>3)phase=3;
        tile=384+(phase<<1);
    }
    /* A contact keeps its direction through hitstop. No clock-driven flips. */
    oamSet(OAM_EFFECT_BASE,fxX-8,fxY-8,3,(fxType&IMPACT_FACING)?0:1,0,tile,2);
    oamSetEx(OAM_EFFECT_BASE,1,OBJ_SHOW);
}

void publishImpactPriority(void) {
    /* NMI's ordinary 544-byte OAM upload starts at zero. After that upload,
     * restore the first OBJ to the EXISTING spark slot while it is visible.
     * OBJ priority bits only order against BG; without rotation an earlier
     * actor can hide an entire low spark. Two vblank register writes, no DMA,
     * no new OAM slots. Actor-to-actor/shadow ordering remains the same.
     * Disable again for quiet combat and all menu screens. */
    if(screen==FIGHT && fxLife) {
        REG_OAMADDL=OAM_EFFECT_BASE>>1;REG_OAMADDH=128;
    } else {REG_OAMADDL=0;REG_OAMADDH=0;}
}

u16 impactScroll(void) {
    s16 offset;
    /* Called after the existing video-clock countdown. Strong: 2,0,-1,0,1,0.
     * Light: 1,0. Guards never shake. Keep vertical scroll at its normal -1.
     * Existing KO/floor countdowns also stay within this two-pixel envelope. */
    offset=0;
    if(shake>5)offset=(shake&1)?1:-1;
    else if(shake==5)offset=2;
    else if(shake==3)offset=-1;
    else if(shake==1)offset=1;
    if(fxType&IMPACT_FACING)offset=-offset;
    return offset&511;
}
#endif
