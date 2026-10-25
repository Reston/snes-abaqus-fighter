#ifndef ABAQUS_SUPER_MOVES_H
#define ABAQUS_SUPER_MOVES_H

/* Action 7 remains the ordinary special ABI. These private, appended arrays
 * distinguish a full-gauge sequence without extending Fighter64, Wave16 or
 * TRACE. No new OBJ, palette, tile upload, sound slot or invulnerability.
 * Include after the last original mutable global and sound()/abs16(). */
#define SUPER_CHORD (KEY_Y|KEY_B)
#define SUPER_VOLLEY 0
#define SUPER_RUSH 1
#define SUPER_RISE 2

typedef struct {
    u8 family,start,activeEnd,recovery,count,gap,window;
    u8 damage,finishDamage,reach,speed,life,lowPattern;
    s16 launchVy;
    u8 firstFrame,nextFrame,finishFrame;
} SuperProfile;

/* Literals stay in ROM; a char[][] would consume initialized WRAM and move
 * the existing pause guide's string arrays with this compiler. */
const char *superNameFor(u8 id) {
    switch(id) {
    case 0:return "KERNEL OVERDRIVE";
    case 1:return "COMPOUND INTEREST";
    case 2:return "ATOMIC CASCADE";
    case 3:return "FINAL BALANCE";
    case 4:return "MACRO COLLAPSE";
    case 5:return "FINAL AUDIT";
    case 6:return "LEGACY ROLLOUT";
    case 7:return "ZERO RISK";
    case 8:return "MERGE STORM";
    case 9:return "CLOUD NINE";
    case 10:return "CLOSING BELL";
    default:return "ABSOLUTE ZERO";
    }
}
/* lowPattern is a bit per projectile, not a guard-breaking/unblockable flag.
 * One existing Wave slot per player serializes every volley. A long-range
 * shot can occupy that slot until expiry; there is never an extra projectile.
 * Direct sequences have gaps, individual confirms and a final knockdown. */
const SuperProfile superProfiles[12]={
    {SUPER_VOLLEY,18,114,36,3,15,4,10,12,18,48,38,0,0,12,12,12},
    {SUPER_VOLLEY,24,106,44,2,30,4,15,19,22,33,56,0,0,12,42,12},
    {SUPER_RUSH,14,44,33,3,13,4,9,14,34,40,0,0,0,6,7,15},
    {SUPER_RUSH,20,48,44,2,23,5,13,21,42,26,0,0,0,15,6,7},
    {SUPER_VOLLEY,26,117,44,2,30,4,15,21,22,30,54,3,0,12,38,8},
    {SUPER_RISE,15,43,38,3,11,5,8,18,36,0,0,0,-57,5,6,13},
    {SUPER_VOLLEY,20,135,33,3,15,4,10,13,21,36,38,7,0,12,8,12},
    {SUPER_RISE,19,43,46,2,16,7,12,22,48,0,0,0,-69,40,6,13},
    {SUPER_VOLLEY,14,104,30,3,10,4,8,13,17,54,30,5,0,8,12,8},
    {SUPER_VOLLEY,22,118,41,2,25,4,14,22,23,42,48,2,0,12,42,8},
    {SUPER_RISE,13,36,36,3,9,4,7,17,33,19,0,0,-72,7,5,13},
    {SUPER_VOLLEY,28,124,38,2,35,4,16,22,27,27,62,1,0,8,42,12}
};

/* 14 bytes total. Each index is one controller's fighter; every round/reset
 * clears all seven arrays. Released super waves retain only their damage tag
 * after an interrupted owner; subsequent ordinary waves clear that tag. */
u8 superActive[2],superRequest[2],superPhase[2],superNext[2];
u8 superContactEnd[2],superWaveDamage[2],superWaveReach[2];

void discardFighterInput(Fighter *f);
u8 verticalContact(Fighter *d,s16 top,s16 bottom);

void resetSupers(void) {
    u8 p;
    for(p=0;p<2;p++) {
        superActive[p]=0;superRequest[p]=0;superPhase[p]=0;superNext[p]=0;
        superContactEnd[p]=0;superWaveDamage[p]=0;superWaveReach[p]=0;
    }
}

/* Consume a held chord even when unavailable: it must never fall through to
 * a normal, quick special or partial gauge spend. Both Y and B must be fresh
 * in the same native sample, with no direction held. A held half-chord cannot
 * arm a super by adding the other button. Hitstop may retain a valid request
 * for the ordinary six live ticks; hurt, wake and airborne never queue it. */
u8 captureSuper(u8 p,u16 keys,u16 edge,u8 live) {
    Fighter *f=&fighters[p];
    if(!live)superRequest[p]=0;
    else if(!hitstop && superRequest[p])superRequest[p]--;
    if((keys&SUPER_CHORD)!=SUPER_CHORD)return 0;
    discardFighterInput(f);
    if(!live)return 1;
    if((edge&SUPER_CHORD)!=SUPER_CHORD)return 1;
    if(keys&(KEY_UP|KEY_DOWN|KEY_LEFT|KEY_RIGHT))return 1;
    if(f->hurt)return 1;
    if(f->downState)return 1;
    if(f->invuln)return 1;
    if(f->y)return 1;
    if(f->action)return 1;
    if(!f->hp)return 1;
    if(f->energy!=ENERGY_MAX)return 1;
    if(waves[p].active)return 1;
    superRequest[p]=INPUT_BUFFER_TICKS;
    return 1;
}

u8 startSuper(u8 p) {
    Fighter *f=&fighters[p];
    const SuperProfile *s;
    if(!superRequest[p])return 0;
    superRequest[p]=0;
    if(f->action)return 0;
    if(f->hurt)return 0;
    if(f->downState)return 0;
    if(f->y)return 0;
    if(f->invuln)return 0;
    if(!f->hp)return 0;
    if(f->energy!=ENERGY_MAX)return 0;
    if(waves[p].active)return 0;
    s=&superProfiles[f->id];
    superActive[p]=1;superPhase[p]=0;superNext[p]=s->start;
    superContactEnd[p]=0;superWaveDamage[p]=0;superWaveReach[p]=0;
    f->energy=0;f->action=7;f->tick=0;f->connected=0;
    f->actionStartup=s->start;f->actionActiveEnd=s->activeEnd;
    f->actionEnd=s->activeEnd+s->recovery;
    f->guard=0;f->duck=0;f->walking=0;f->counter=0;f->airAction=0;
    f->vx=0;f->vy=0;f->motion=0;f->downbuffer=0;
    discardFighterInput(f);
    /* Charge ring uses the existing contact cell, never an extra OBJ. */
    if(!fxLife){fxX=f->x>>4;fxY=FLOOR-48;fxLife=6;fxType=1;}
    hudDirty=1;sound(2);return 1;
}

void syncSuper(u8 p) {
    Fighter *f=&fighters[p];
    if(!waves[p].active){superWaveDamage[p]=0;superWaveReach[p]=0;}
    if(!superActive[p])return;
    if(f->action!=7)superActive[p]=0;
    if(f->hurt)superActive[p]=0;
    if(f->downState)superActive[p]=0;
    if(!f->hp)superActive[p]=0;
    if(!superActive[p]){superRequest[p]=0;superContactEnd[p]=0;}
}

void updateSuper(u8 p) {
    Fighter *f=&fighters[p];Wave *w=&waves[p];
    const SuperProfile *s=&superProfiles[f->id];
    u8 phase;
    if(f->tick>=s->activeEnd)return;
    if(f->tick<s->start)return;
    if(s->family!=SUPER_VOLLEY && f->tick<superContactEnd[p])
        f->x+=f->face?s->speed:-s->speed;
    if(superPhase[p]>=s->count)return;
    if(f->tick<superNext[p])return;
    if(s->family==SUPER_VOLLEY && w->active)return;
    phase=superPhase[p];superPhase[p]++;
    superNext[p]=f->tick+s->gap;
    superContactEnd[p]=f->tick+s->window;
    f->connected=0;
    if(s->family==SUPER_VOLLEY) {
        w->active=1;w->owner=p;w->face=f->face;w->speed=s->speed;
        w->low=(s->lowPattern>>phase)&1;
        w->x=f->x+(f->face?22*16:-22*16);w->y=w->low?FLOOR-18:FLOOR-39;
        w->life=s->life;superWaveReach[p]=s->reach;
        superWaveDamage[p]=superPhase[p]==s->count?s->finishDamage:s->damage;
        /* Once the last shot leaves, finish its release and enter ordinary
         * recovery. The longer initial emission window only bounds delayed
         * volleys when the single wave slot is occupied at long range. */
        if(superPhase[p]==s->count) {
            f->actionActiveEnd=f->tick+s->window;
            if(f->actionActiveEnd>s->activeEnd)f->actionActiveEnd=s->activeEnd;
            f->actionEnd=f->actionActiveEnd+s->recovery;
        }
    } else if(s->family==SUPER_RISE && superPhase[p]==s->count) {
        f->vy=s->launchVy;f->y=-1;f->vx=0;
    }
    sound(2);
}

u8 superCanHit(u8 p) {
    Fighter *f=&fighters[p];Fighter *d=&fighters[1-p];
    const SuperProfile *s=&superProfiles[f->id];
    s16 dx;
    if(s->family==SUPER_VOLLEY)return 0;
    if(!superPhase[p])return 0;
    if(f->tick>=superContactEnd[p])return 0;
    if(f->connected)return 0;
    if(f->hurt)return 0;
    if(f->downState)return 0;
    if(d->downState)return 0;
    if(d->invuln)return 0;
    if(!d->hp)return 0;
    dx=d->x-f->x;
    if(dx>0 && !f->face)return 0;
    if(dx<0 && f->face)return 0;
    if(abs16(dx)>(s->reach+BODY_HALF_WIDTH)*16)return 0;
    return verticalContact(d,f->y-72*16,f->y-12*16);
}

u8 superDamage(u8 p,u8 ordinary) {
    const SuperProfile *s;
    if(!superActive[p])return ordinary;
    s=&superProfiles[fighters[p].id];
    return superPhase[p]==s->count?s->finishDamage:s->damage;
}

u8 superKnockdown(u8 p) {
    return superPhase[p]==superProfiles[fighters[p].id].count;
}

u8 superFrame(u8 p) {
    Fighter *f=&fighters[p];
    const SuperProfile *s=&superProfiles[f->id];
    /* Three disjoint whole-body drawings, authored for each signature.
     * v0.25 retimes the profile but keeps every pulse and its damage. A volley
     * returns to its charge between releases instead of holding a cast
     * throughout the potentially long single-Wave wait. */
    if(f->tick<s->start)return 1;
    if(f->tick>=f->actionActiveEnd)return 4;
    if(f->tick<superContactEnd[p])return 2;
    return 1;
}

/* Fill previously empty guide rows, retaining the original specials help,
 * names, families and three-tick 1472-byte publish contract. */
void drawSuperGuide(void) {
    drawGuideWord(7*64+3*2,"SUPER: Y+B NEUTRAL FULL 96");
    drawGuideWord(16*64+3*2,"P1");
    drawGuideWord(16*64+6*2,superNameFor(fighters[0].id));
    drawGuideWord(21*64+3*2,"P2");
    drawGuideWord(21*64+6*2,superNameFor(fighters[1].id));
}

#endif
