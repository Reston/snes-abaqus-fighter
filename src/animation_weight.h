/* Presentation only. Included at the original animateFighter hook, after
 * Fighter, profiles and knockdown definitions. No mutable state, geometry,
 * action timing, physics, damage, transfer or TRACE changes.
 *
 * Existing animState 0..14 keep their meanings; 15 is a six-tick visual
 * landing release. Any real input/state wins immediately over that release.
 * All clocks remain under animationAdvance (pause/hitstop freeze).
 * Feature 04 may own the roundEnd winner branch (state 8) and intro override.
 */
void animateFighter(u8 p) {
    Fighter *f=&fighters[p];
    const CharacterProfile *c=combatProfiles[p];
    u8 state,previous,start,end,recover,hold,phase,action=f->action,tick;
    previous=f->animState;
    if(roundEnd) {
        if(!f->hp)state=9;
        else if(winner==p)state=8;
        else state=7;
    } else if(f->downState)state=9+f->downState;
    else if(f->hurt)state=f->guard?6:7;
    else if(action)state=5;
    else if(f->y || f->landing)state=4;
    else if(f->duck)state=3;
    else if(f->walking)state=f->walking==1?1:2;
    else if(f->guard)state=6;
    else {
        state=0;
        /* Compression is already over; this never extends landing physics
         * or delays an attack, jump, guard or step. */
        if(previous==4)state=15;
        else if(previous==15 && f->animTick<6)state=15;
    }
    if(previous!=state) {
        f->animState=state;f->animTick=0;
        /* Reclaim guard after locomotion/attacks rather than snapping into
         * an arbitrary breath pose. Initial roster phases remain staggered. */
        if(state==0)f->animTick=previous==255?(f->id*3)&63:60;
        if(state==1 || state==2)f->stride=0;
    }
    if(state==0) {
        /* 96-tick breath: long planted guard, quick inhale, slower exhale,
         * then recovery. Unequal holds avoid an even four-frame metronome. */
        tick=f->animTick;
        if(tick<32)f->animFrame=16;
        else if(tick<44)f->animFrame=17;
        else if(tick<60)f->animFrame=18;
        else if(tick<72)f->animFrame=19;
        else f->animFrame=16;
        f->animTick++;if(f->animTick>=96)f->animTick=0;
        return;
    }
    if(state==1 || state==2) {
        /* Eight authored contact/recoil/pass/extension poses. Distance owns
         * the gait: 32px forward or a guarded 16px retreat per full cycle.
         * Reverse the same footfalls for retreat; no new mutable clock. */
        phase=state==1?((f->stride>>6)&7):((f->stride>>5)&7);
        if(state==2)phase=(8-phase)&7;
        f->animFrame=20+phase;
    }
    else if(state==3)f->animFrame=f->animTick<4?28:3;
    else if(state==4) {
        if(f->landing)f->animFrame=31;
        else if(f->animTick<2)f->animFrame=29;
        else if(f->animTick<6)f->animFrame=30;
        /* Bent-knee descent keeps compression for actual ground contact. */
        else if(f->vy>32 && f->y>-24*16)f->animFrame=54;
        else f->animFrame=55;
    } else if(state==6) {
        if(f->duck)f->animFrame=3;
        else f->animFrame=f->animTick<3?40:9;
    }
    else if(state==7)f->animFrame=f->animTick<6?10:41;
    /* Retain the winner hook for feature 04. */
    else if(state==8)f->animFrame=personalityVictoryFrame(f->id);
    else if(state==9) {
        if(f->downState==DOWN_FLOOR)f->animFrame=f->downTick<5?59:14;
        else if(f->animTick<8)f->animFrame=47;
        else f->animFrame=f->animTick<16?59:14;
    }
    else if(state==10)f->animFrame=58;
    else if(state==11) {
        /* Throw ownership retains its lifted silhouette through ascent.
         * Ordinary knockdowns use recoil. Fall starts at the physical apex,
         * independently of fighter gravity and the knockdown tick count. */
        if(f->vy<0)f->animFrame=f->downOwner<2?58:60;
        else f->animFrame=61;
    }
    else if(state==12)f->animFrame=f->downTick<5?59:14;
    else if(state==13)f->animFrame=f->downTick<6?62:63;
    else if(state==14)f->animFrame=63;
    else if(state==15)f->animFrame=f->animTick<3?28:19;
    else {
        start=f->actionStartup;end=f->actionActiveEnd;
        tick=f->tick;hold=tick<start;recover=tick>=end;
        if(superActive[p])f->animFrame=superFrame(p);
        else if(f->airAction) {
            if(action<=3)f->animFrame=hold?49:(recover?51:50);
            else f->animFrame=hold?52:(recover?54:53);
            if(recover && tick+4>=f->actionEnd)f->animFrame=55;
        }
        else if(action==1) {
            f->animFrame=hold?32:(recover?33:5);
            if(recover && tick+3>=f->actionEnd)f->animFrame=32;
        }
        else if(action==2 || action==3) {
            if(hold)f->animFrame=tick<3?32:34;
            else if(!recover)f->animFrame=6;
            else if(tick<end+2)f->animFrame=6;
            else f->animFrame=tick+4<f->actionEnd?35:32;
        }
        else if(action>=4 && action<=6) {
            if(f->duck) {
                if(hold)f->animFrame=tick<3?28:38;
                else if(!recover)f->animFrame=8;
                else if(tick<end+2)f->animFrame=8;
                else f->animFrame=tick+4<f->actionEnd?39:28;
            } else {
                if(hold)f->animFrame=(action==4 || tick>=3)?36:32;
                else if(!recover)f->animFrame=7;
                else if(action!=4 && tick<end+2)f->animFrame=7;
                else f->animFrame=tick+4<f->actionEnd?37:32;
            }
        } else if(action==7) {
            if(c->specialFamily==SPECIAL_RUSH) {
                if(hold)f->animFrame=tick<3?32:34;
                else if(!recover)f->animFrame=15;
                else f->animFrame=tick+4<f->actionEnd?33:32;
            }
            else if(c->specialFamily==SPECIAL_RISING)f->animFrame=hold?44:(recover?45:13);
            else {
                f->animFrame=hold?42:(tick<end+7?12:43);
                if(recover && tick+4>=f->actionEnd)f->animFrame=32;
            }
        } else if(action==8)f->animFrame=hold?44:(recover?45:13);
        else if(action==9)f->animFrame=hold?56:(tick<start+8?57:48);
        else f->animFrame=hold?34:(recover?35:15);
    }
    if(f->animTick<200)f->animTick++;
}
