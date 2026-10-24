/* Explicit throw ownership and bounded recovery; included after hurt(). */
void clearWakeInput(Fighter *f) {
    f->wakeAction=0;f->wakeAge=0;f->wakeJump=0;f->wakeKeys=0;
}
void clampDowned(Fighter *f) {
    if(f->x<24*16)f->x=24*16;
    if(f->x>232*16)f->x=232*16;
}
void clearThrowLinks(void) {
    u8 p;
    for(p=0;p<2;p++) {
        fighters[p].throwVictim=255;fighters[p].downOwner=255;
        fighters[p].downDamage=0;clearWakeInput(&fighters[p]);
    }
}
void releaseHeldVictim(u8 owner) {
    Fighter *a=&fighters[owner];Fighter *d;
    u8 victim=a->throwVictim;
    a->throwVictim=255;
    if(victim>1)return;
    d=&fighters[victim];
    if(d->downState!=DOWN_LIFT || d->downOwner!=owner)return;
    d->downDamage=0;d->downOwner=255;
    d->downState=DOWN_FLIGHT;d->downTick=0;d->vx=0;d->vy=0;
}
void beginKnockdown(u8 owner,u8 victim,u8 direction) {
    Fighter *d=&fighters[victim];
    releaseHeldVictim(victim);
    d->downState=DOWN_FLIGHT;d->downTick=0;d->downOwner=255;d->downDamage=0;
    d->action=0;d->tick=0;d->connected=0;d->guard=0;d->duck=0;d->walking=0;d->airAction=0;
    /* Downed art follows the launch direction, then wake restores facing. */
    d->face=direction;d->vx=direction?24:-24;d->vy=-40;
    if(!d->y)d->y=-1;
    discardFighterInput(d);clearWakeInput(d);d->motion=0;d->downbuffer=0;
}
u8 knockdownAttack(u8 owner,u8 action,u8 low) {
    if(action==8)return 1;
    if(action==6 && low)return 1;
    if(action==7 && combatProfiles[owner]->specialFamily==SPECIAL_RISING)return 1;
    return 0;
}
void beginThrow(u8 owner,u8 victim) {
    Fighter *a=&fighters[owner];Fighter *d=&fighters[victim];
    a->connected=2;a->throwVictim=victim;
    d->downState=DOWN_LIFT;d->downTick=0;d->downOwner=owner;
    d->downDamage=attackDamage(combatProfiles[owner],a->id,9);
    d->action=0;d->tick=0;d->connected=0;d->hurt=0;d->guard=0;d->duck=0;d->walking=0;
    d->airAction=0;d->vx=0;d->vy=0;d->face=a->face;
    d->x=a->x+(a->face?16*16:-16*16);d->y=-8*16;clampDowned(d);
    d->combo=0;d->combotime=0;d->counter=0;
    discardFighterInput(d);clearWakeInput(d);d->motion=0;d->downbuffer=0;
    hitstop=3;fxType=1;fxLife=6;fxX=d->x>>4;fxY=FLOOR-40;sound(1);
}
void throwTech(void) {
    u8 p;
    for(p=0;p<2;p++) {
        fighters[p].action=0;fighters[p].tick=0;fighters[p].connected=1;
        fighters[p].hurt=6;fighters[p].guard=1;fighters[p].airAction=0;
        fighters[p].combo=0;fighters[p].combotime=0;fighters[p].counter=0;
        fighters[p].x+=fighters[p].face?-64:64;
        discardFighterInput(&fighters[p]);clearWakeInput(&fighters[p]);
    }
    clearThrowLinks();clearBanner();hitstop=3;fxType=1;fxLife=6;
    /* Explain an earned simultaneous-throw escape without changing it.
     * Reuse the existing deferred banner after both actor uploads settle. */
    impactBannerCounter=3;impactBannerCombo=0;impactBannerPending=1;impactSettle=1;
    fxX=(fighters[0].x+fighters[1].x)>>5;fxY=FLOOR-40;sound(1);
}
void updateDowned(u8 p) {
    Fighter *f=&fighters[p];Fighter *a;
    u8 owner,damage;
    if(f->hurt)f->hurt--;
    f->downTick++;
    if(f->downState==DOWN_LIFT) {
        if(f->downOwner>1){f->downState=DOWN_FLIGHT;f->downTick=0;f->downDamage=0;f->vy=0;f->vx=0;return;}
        a=&fighters[f->downOwner];
        f->x=a->x+(a->face?16*16:-16*16);f->y=-(8+f->downTick*2)*16;
        if(f->downTick>=6) {
            a->throwVictim=255;f->downState=DOWN_FLIGHT;f->downTick=0;
            f->vx=a->face?48:-48;f->vy=-56;
        }
    } else if(f->downState==DOWN_FLIGHT) {
        f->x+=f->vx;f->y+=f->vy;f->vy+=combatProfiles[p]->gravity;
        if(f->y>=0) {
            f->y=0;f->vx=0;f->vy=0;f->downState=DOWN_FLOOR;f->downTick=0;
            owner=f->downOwner;damage=f->downDamage;
            f->downOwner=255;f->downDamage=0;
            if(damage && owner<2)hurt(owner,p,damage,0,0,1);
            else {fxX=f->x>>4;fxY=FLOOR-4;fxType=0;fxLife=6;shake=3;}
        }
    } else if(f->downState==DOWN_FLOOR) {
        if(f->downTick>=18 && (f->hp || mode==2)) {
            f->downState=DOWN_RISE;f->downTick=0;
            f->face=f->x<fighters[1-p].x?1:0;
        }
    } else if(f->downState==DOWN_RISE) {
        if(f->downTick>=10) {
            f->downState=DOWN_WAKE;f->downTick=0;
            f->face=f->x<fighters[1-p].x?1:0;clearWakeInput(f);
        }
    } else if(f->downState==DOWN_WAKE && f->downTick>=6) {
        f->downState=DOWN_FREE;f->downTick=0;f->hurt=0;f->guard=0;
        f->face=f->x<fighters[1-p].x?1:0;
        f->invuln=4;f->wakeJust=1;f->wakeLock=f->wakeJump?0:1;
        if(f->wakeAction && f->wakeAge) {
            f->bufferedAction=f->wakeAction;f->bufferAge=f->wakeAge+1;f->bufferKeys=f->wakeKeys;
        }
        if(f->wakeJump)f->jumpBuffer=f->wakeJump+1;
        clearWakeInput(f);
    }
    clampDowned(f);
}
