#ifndef ABAQUS_DEFENSE29_H
#define ABAQUS_DEFENSE29_H

/* Only bytes 0/1 of our initialized 16-byte reservation are live timers.
 * Ten contact ticks include the DOWN_WAKE -> FREE tick: general invuln
 * retains ticks 0..4, then only throws are rejected on ticks 5..9.
 * Decrement once at combat entry; pause/intro/hitstop never call combat.
 * No Fighter, profile, normal, trace, DMA or animation allocation changes. */
#define DEFENSE29_WAKE_TICKS 10
#define DEFENSE29_LAST_TECH_TICK 5

void defense29Reset(void) {
    u8 p;
    for(p=0;p<16;p++)v29DefenseState[p]=0;
}

/* One fallible CPU observation, after two visible live lift ticks. It emits
 * the same fresh command as a player, never reads pads or changes the PRNG.
 * Easy declines; Normal/Hard accept 1/4 or 1/2 of the existing frame phases.
 * No retry, pre-grab prediction, hitstop buffering or guaranteed escape. */
u16 defense29CpuKeys(void) {
    u16 toward,phase;
    if(hitstop)return 0;
    if(difficulty==0)return 0;
    if(fighters[1].downTick!=2)return 0;
    phase=(frame+fighters[1].id*13)&3;
    if(difficulty==1 && phase)return 0;
    if(difficulty==2 && phase>=2)return 0;
    if(fighters[0].x>fighters[1].x)toward=KEY_RIGHT;
    else if(fighters[0].x<fighters[1].x)toward=KEY_LEFT;
    else toward=fighters[0].face?KEY_LEFT:KEY_RIGHT;
    return toward|KEY_X;
}

/* Called only for a linked lift, AFTER the original downed update. Thus
 * ticks 1..5 are eligible; tick 6 already launched and can never be undone.
 * captureInput still samples edges while downed, but discards normal buffers.
 * Toward uses the actual owner side: lift art intentionally faces away.
 * Down+X remains uppercut, and SOCD is cleaned by the existing input path. */
void defense29TryTech(u8 victim) {
    Fighter *d=&fighters[victim];Fighter *a;
    u16 toward;
    s16 left;
    u8 owner;
    if(!d->downTick)return;
    if(d->downTick>DEFENSE29_LAST_TECH_TICK)return;
    if(!(d->inputEdge&KEY_X))return;
    if(d->keys&KEY_DOWN)return;
    if((edge0|edge1)&KEY_START)return;
    if(!d->hp)return;
    owner=d->downOwner;if(owner>1)return;
    a=&fighters[owner];
    if(!a->hp)return;
    if(a->downState)return;
    if(a->hurt)return;
    if(a->action!=9)return;
    if(a->throwVictim!=victim)return;
    if(a->x>d->x)toward=KEY_RIGHT;
    else if(a->x<d->x)toward=KEY_LEFT;
    else toward=a->face?KEY_LEFT:KEY_RIGHT;
    if(!(d->keys&toward))return;

    /* Cancel ownership and its deferred landing damage BEFORE presentation.
     * Reuse the established six-tick mutual guard recovery / three-tick
     * contact pause and deferred THROW TECH cue, with no new render transfer. */
    d->downState=DOWN_FREE;d->downTick=0;d->downDamage=0;d->downOwner=255;
    d->y=0;d->vx=0;d->vy=0;d->invuln=0;d->wakeJust=0;d->wakeLock=0;
    a->face=toward==KEY_LEFT?1:0;d->face=a->face?0:1;
    throwTech();
    clearRecoil(0);clearRecoil(1);

    /* Symmetric 40px separation exceeds every original throw range. If a
     * wall limits one fighter, the other takes the remaining displacement.
     * Keep the same left/right order; never teleport through the opponent. */
    left=((fighters[0].x+fighters[1].x)>>1)-20*16;
    if(left<24*16)left=24*16;
    if(left>192*16)left=192*16;
    if(a->face){a->x=left;d->x=left+40*16;}
    else {d->x=left;a->x=left+40*16;}
    a->walking=0;a->duck=0;d->walking=0;d->duck=0;
    v29DefenseState[0]=0;v29DefenseState[1]=0;
    fxX=(fighters[0].x+fighters[1].x)>>5;
    /* Audio feature integration: preserve this semantic guard-contact hook. */
    soundImpact(SOUND_GUARD);
}

#endif
