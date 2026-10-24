/* Presentation only. Included at the original animateFighter hook, after
 * Fighter, profiles and knockdown definitions. No mutable state, geometry,
 * action timing, physics, damage, transfer or TRACE changes.
 *
 * Existing animState 0..14 keep their meanings; 15 is a six-tick visual
 * landing release. Any real input/state wins immediately over that release.
 * All clocks remain under animationAdvance (pause/hitstop freeze).
 * Feature 04 may own the roundEnd winner branch (state 8) and intro override.
 */
/* Resolve the two ordinary actors to absolute WRAM operands. 816-tcc
 * otherwise reconstructs its generic far pointer for every animation field.
 * Both expansions share this exact selector/clock template; no state or
 * timing is cached across calls and every existing write stays in order. */
#define ANIMATE_FIGHTER_AT(F,P) do { \
    const CharacterProfile *c=combatProfiles[P]; \
    u8 state,previous,start,end,recover,hold,phase,action=(F).action,tick; \
    previous=(F).animState; \
    if(roundEnd) { \
        if(!(F).hp)state=9; \
        else if(winner==(P))state=8; \
        else state=7; \
    } else if((F).downState)state=9+(F).downState; \
    else if((F).hurt)state=(F).guard?6:7; \
    else if(action)state=5; \
    else if((F).y || (F).landing)state=4; \
    else if((F).duck)state=3; \
    else if((F).walking)state=(F).walking==1?1:2; \
    else if((F).guard)state=6; \
    else { \
        state=0; \
        /* Compression is already over; this never extends landing physics \
         * or delays an attack, jump, guard or step. */ \
        if(previous==4)state=15; \
        else if(previous==15 && (F).animTick<6)state=15; \
    } \
    if(previous!=state) { \
        (F).animState=state;(F).animTick=0; \
        /* Reclaim guard after locomotion/attacks rather than snapping into \
         * an arbitrary breath pose. Initial roster phases remain staggered. */ \
        if(state==0)(F).animTick=previous==255?((F).id*3)&63:60; \
        if(state==1 || state==2)(F).stride=0; \
    } \
    if(state==0) { \
        /* 96-tick breath: long planted guard, quick inhale, slower exhale, \
         * then recovery. Unequal holds avoid an even four-frame metronome. */ \
        tick=(F).animTick; \
        if(tick<32)(F).animFrame=16; \
        else if(tick<44)(F).animFrame=17; \
        else if(tick<60)(F).animFrame=18; \
        else if(tick<72)(F).animFrame=19; \
        else (F).animFrame=16; \
        (F).animTick++;if((F).animTick>=96)(F).animTick=0; \
        return; \
    } \
    if(state==1 || state==2) { \
        /* Shared artwork has one physical step length in either direction. \
         * Eight phases cover 32px; the slower retreat naturally takes longer. \
         * Four pixels per pose also lets both actors publish each footfall \
         * under the existing one-actor-per-vblank transfer budget. */ \
        phase=((F).stride>>6)&7; \
        if(state==2)phase=(8-phase)&7; \
        (F).animFrame=20+phase; \
    } \
    else if(state==3)(F).animFrame=(F).animTick<4?28:3; \
    else if(state==4) { \
        if((F).landing)(F).animFrame=31; \
        else if((F).animTick<2 && (F).y>-24*16 && (F).vy < -32)(F).animFrame=29; \
        /* The physical velocity, rather than an arbitrary elapsed hold, \
         * separates extension, the compact apex and the open-leg descent. \
         * Two compression samples introduce takeoff without delaying input. */ \
        else if((F).vy < -32)(F).animFrame=30; \
        else if((F).vy > 32)(F).animFrame=54; \
        else (F).animFrame=55; \
    } else if(state==6) { \
        if((F).duck)(F).animFrame=3; \
        /* The brace is contact feedback, never a neutral back-guard pose. */ \
        else (F).animFrame=(F).hurt>4?40:9; \
    } \
    /* Hold the backward impact through the recoil; recover only as stun ends. \
     * The clock and gameplay hurt timer already freeze together in hitstop. */ \
    else if(state==7)(F).animFrame=(F).hurt>6?10:41; \
    /* Retain the winner hook for feature 04. */ \
    else if(state==8)(F).animFrame=personalityVictoryFrame((F).id); \
    else if(state==9) { \
        if((F).downState==DOWN_FLOOR)(F).animFrame=(F).downTick<5?59:14; \
        else if((F).animTick<8)(F).animFrame=47; \
        else (F).animFrame=(F).animTick<16?59:14; \
    } \
    else if(state==10)(F).animFrame=58; \
    else if(state==11) { \
        /* Throw ownership retains its lifted silhouette through ascent. \
         * Ordinary knockdowns use recoil. Fall starts at the physical apex, \
         * independently of fighter gravity and the knockdown tick count. */ \
        if((F).vy<0)(F).animFrame=(F).downOwner<2?58:60; \
        else (F).animFrame=61; \
    } \
    else if(state==12)(F).animFrame=(F).downTick<5?59:14; \
    else if(state==13)(F).animFrame=(F).downTick<6?62:63; \
    else if(state==14)(F).animFrame=63; \
    /* The same open-leg drawing releases the grounded squat. Any accepted \
     * command selected above wins immediately; there is no landing lock. */ \
    else if(state==15)(F).animFrame=54; \
    else { \
        start=(F).actionStartup;end=(F).actionActiveEnd; \
        tick=(F).tick;hold=tick<start;recover=tick>=end; \
        if(superActive[P])(F).animFrame=superFrame(P); \
        else if((F).airAction) { \
            if(action<=3)(F).animFrame=hold?49:(recover?51:50); \
            else (F).animFrame=hold?52:(recover?54:53); \
            /* Recover the arms/leg before returning to the physical flight \
             * phase. An attack finishing on descent must not tuck at apex. */ \
            if(recover && tick+4>=(F).actionEnd) { \
                if((F).vy < -32)(F).animFrame=30; \
                else if((F).vy > 32)(F).animFrame=54; \
                else (F).animFrame=55; \
            } \
        } \
        else if(action==1) { \
            (F).animFrame=hold?32:(recover?33:5); \
            if(recover && tick+3>=(F).actionEnd)(F).animFrame=32; \
        } \
        else if(action==2 || action==3) { \
            if(hold)(F).animFrame=tick<3?32:34; \
            else if(!recover)(F).animFrame=6; \
            else (F).animFrame=tick+4<(F).actionEnd?35:32; \
        } \
        else if(action>=4 && action<=6) { \
            if((F).duck) { \
                if(hold)(F).animFrame=tick<3?28:38; \
                else if(!recover)(F).animFrame=8; \
                else (F).animFrame=tick+4<(F).actionEnd?39:28; \
            } else { \
                if(hold)(F).animFrame=(action==4 || tick>=3)?36:32; \
                else if(!recover)(F).animFrame=7; \
                else (F).animFrame=tick+4<(F).actionEnd?37:32; \
            } \
        } else if(action==7) { \
            if(c->specialFamily==SPECIAL_RUSH) { \
                if(hold)(F).animFrame=tick<3?32:34; \
                else if(!recover)(F).animFrame=15; \
                else (F).animFrame=tick+4<(F).actionEnd?33:32; \
            } \
            else if(c->specialFamily==SPECIAL_RISING)(F).animFrame=hold?44:(recover?45:13); \
            else { \
                /* The projectile emits on one tick, but two actors share one \
                 * pose upload per vblank. Keep its authored release hold so \
                 * neither port can lose the cast before VRAM publishes it. */ \
                (F).animFrame=hold?42:(tick<end+7?12:43); \
                if(recover && tick+4>=(F).actionEnd)(F).animFrame=32; \
            } \
        } else if(action==8)(F).animFrame=hold?44:(recover?45:13); \
        else if(action==9)(F).animFrame=hold?56:(tick<start+8?57:48); \
        else (F).animFrame=hold?34:(recover?35:15); \
    } \
    if((F).animTick<200)(F).animTick++; \
} while(0)

void animateFighter(u8 p) {
    if(p) { ANIMATE_FIGHTER_AT(fighters[1],1); }
    else { ANIMATE_FIGHTER_AT(fighters[0],0); }
}
#undef ANIMATE_FIGHTER_AT
