#ifndef ABAQUS_PACING_RECOIL_H
#define ABAQUS_PACING_RECOIL_H

/* One existing byte, two private nibbles: bits 0..1 contact direction
 * (1 left / 2 right), bit 2 strong, bit 3 direct-super linking pulse.
 * No Fighter/Wave/TRACE or RAM changes.
 * Never consult the attacker's later facing: trades, landing and crossing
 * cannot turn a hurt reaction around. applyHitReaction remains the audited
 * native 16+floor(damage/3) transition; this module only moves its victim. */
void clearRecoil(u8 p) {
    rearKickRecoil&=p?15:240;
}

/* Reuse hurtWithRecoil's existing victim pointer. 816-tcc does not inline a
 * C helper, so avoid rebuilding it and pushing four byte arguments twice on
 * simultaneous contact. This is the same immediate latch/impulse operation;
 * recoilAction stays private so linked supers keep strong presentation. */
#define BEGIN_RECOIL_AT(f,p,direction,action,blocked) do { \
    u8 recoilLatch=(direction)+1,recoilStep,recoilAction=(action); \
    u8 opponent=1-(p); \
    const SuperProfile *recoilProfile; \
    rearKickRecoil&=(p)?15:240; \
    if(superActive[opponent]) { \
        recoilProfile=&superProfiles[fighters[opponent].id]; \
        if(superPhase[opponent]<recoilProfile->count) { \
            if(recoilProfile->family!=SUPER_VOLLEY){recoilAction=1;recoilLatch|=8;} \
        } \
    } \
    if(blocked)recoilStep=16; \
    else if(recoilAction==1 || recoilAction==4)recoilStep=32; \
    else {recoilLatch|=4;recoilStep=64;} \
    if(p)recoilLatch<<=4; \
    rearKickRecoil|=recoilLatch; \
    (f)->x+=(direction)?recoilStep:-recoilStep; \
} while(0)

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
        /* Linking guards keep the prior one-pixel impulse; added travel
         * before a stationary rising finisher would make it whiff. */
        if(latch&8)step=0;
        else if(remaining>=6)step=8;
        else if(remaining>=3)step=6;
        else step=4;
    } else if(latch&8) {
        /* v0.25 adds four hurt ticks for readable ordinary hit reactions.
         * Direct linked supers retain their old drift clock and distance;
         * longer contact pauses provide their slower real-time rhythm. */
        if(remaining>4)remaining-=4;else remaining=0;
        /* Never exceed the old nine-unit per-tick drift before a linked
         * pulse. Rising families have no forward rush to regain that range. */
        if(!remaining)step=0;
        else if(remaining>=12)step=8;
        else if(remaining>=8)step=6;
        else if(remaining>=4)step=4;
        else step=2;
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

/* v0.25 slower launch balances the longer jump arc, preserving nominal travel.
 * A switch emits ROM immediates rather than another initialized RAM table.
 * Jump owner may replace this hook with its approved full arc implementation. */
u8 pacingAirSpeed(u8 id) {
    switch(id) {
    case 0:return 22;case 1:return 19;case 2:return 25;case 3:return 22;
    case 4:return 21;case 5:return 23;case 6:return 22;case 7:return 23;
    case 8:return 28;case 9:return 21;case 10:return 26;default:return 23;
    }
}

#endif
