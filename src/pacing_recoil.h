#ifndef ABAQUS_PACING_RECOIL_H
#define ABAQUS_PACING_RECOIL_H

/* One existing byte, two private nibbles: bits 0..1 contact direction
 * (1 left / 2 right), bit 2 strong. No Fighter/Wave/TRACE or RAM changes.
 * Never consult the attacker's later facing: trades, landing and crossing
 * cannot turn a hurt reaction around. applyHitReaction remains the audited
 * native 12+floor(damage/3) transition; this module only moves its victim. */
void clearRecoil(u8 p) {
    rearKickRecoil&=p?15:240;
}

void beginRecoil(u8 p,u8 direction,u8 action,u8 blocked) {
    Fighter *f=&fighters[p];
    u8 latch=direction+1,step;
    clearRecoil(p);
    if(blocked)step=16;
    else if(action==1 || action==4)step=32;
    else {latch|=4;step=64;}
    if(p)latch<<=4;
    rearKickRecoil|=latch;
    f->x+=direction?step:-step;
}

void updateRecoil(u8 p) {
    Fighter *f=&fighters[p];
    u8 latch,step,remaining;
    latch=p?(rearKickRecoil>>4):(rearKickRecoil&15);
    if(!(latch&3))return; /* Throw-tech is not a fresh strike contact. */
    remaining=f->hurt;
    /* Descending 12.4 impulses, bounded by existing stun. Guards travel
     * less than light hits; strong hits double the live drift. No extra
     * stun, hitstop, invulnerability, pressure timer or game-clock slowdown. */
    if(f->guard) {
        if(remaining>=6)step=8;
        else if(remaining>=3)step=6;
        else step=4;
    } else {
        if(remaining>=12)step=16;
        else if(remaining>=8)step=12;
        else if(remaining>=4)step=8;
        else step=4;
        if(latch&4)step<<=1;
    }
    f->x+=(latch&3)==2?step:-step;
    if(!remaining)clearRecoil(p);
}

/* Ground walking is slower; keep the pre-revision jump horizontal launch.
 * A switch emits ROM immediates rather than another initialized RAM table.
 * Jump owner may replace this hook with its approved full arc implementation. */
u8 pacingAirSpeed(u8 id) {
    switch(id) {
    case 0:return 28;case 1:return 25;case 2:return 32;case 3:return 29;
    case 4:return 24;case 5:return 28;case 6:return 25;case 7:return 26;
    case 8:return 34;case 9:return 26;case 10:return 32;default:return 27;
    }
}

#endif
