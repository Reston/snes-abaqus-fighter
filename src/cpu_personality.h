#ifndef ABAQUS_CPU_PERSONALITY_H
#define ABAQUS_CPU_PERSONALITY_H

/* Fictional fighting habits, not claims about the people in the roster.
 * ROM-only policy: no new WRAM, fighter fields, trace words or timers.
 * All thresholds use the existing one-per-decision 0..31 PRNG sample.
 * Primary/secondary are Y, X, B, A indices; every command goes through
 * captureInput/controls with ordinary startup, meter and collision rules. */
typedef struct {
    u8 spacing,tempo,retreat,counter,throws,primary,secondary,pressure,guard;
} CpuPersonality;
typedef char CpuPersonalityMustBeNineBytes[sizeof(CpuPersonality)==9?1:-1];

const CpuPersonality cpuPersonalities[12]={
    /*                  px tick back punish throw main alt close guard */
    /* Damian: balanced punches and checks. */
    {35,18, 8,10,12,0,2,26,2},
    /* Ivo: patient long kicks, gives ground. */
    {44,23,24,12, 6,2,3,14,6},
    /* Cristobal: fast light pressure. */
    {29,12, 3, 6,12,0,2,31,0},
    /* Cote: closes for throws and strong punches. */
    {26,17, 4, 8,28,1,3,30,1},
    /* Negger: slow heavy checks behind a guard. */
    {43,24,20,14,10,3,1,16,5},
    /* David: waits for recovery, answers with a jab. */
    {38,21,16,27, 8,1,0,20,4},
    /* Fernando: keeps the longest space with kicks. */
    {46,22,26,10, 4,2,3,12,6},
    /* Cristian: bait and strong-punch recovery answers. */
    {40,20,18,29, 6,2,1,18,4},
    /* Mamariaga: forward strong-kick pressure and throws. */
    {31,14, 5, 7,18,3,2,30,1},
    /* Reston: mobile light punches and strong-kick checks. */
    {36,16,12,16, 8,0,3,25,2},
    /* Roxana: close kick pressure, quick recovery counters. */
    {32,15, 8,24,16,2,0,29,3},
    /* Lars: deliberate strong punches and kick counters. */
    {42,23,22,22,10,1,2,16,5}
};

u16 cpuNormalKey(u8 choice) {
    if(choice==0)return KEY_Y;
    if(choice==1)return KEY_X;
    if(choice==2)return KEY_B;
    return KEY_A;
}

u16 cpuKeys(void) {
    s16 distance;
    u16 k=0,forward,back,waveDistance,specialMax;
    u8 chance,enemyActive,waveApproaching,tempo,threshold,choice;
    Fighter *f=&fighters[1];Fighter *enemy=&fighters[0];
    const CharacterProfile *c=combatProfiles[1];
    const CpuPersonality *habit;
    if(mode==2 && trainingDummy<4)return trainingKeys();
    if(!f->hp)return 0;
    if(!enemy->hp)return 0;
    if(f->downState && f->downState!=DOWN_WAKE)return 0;
    /* The single existing wake edge retains captureInput's six-tick buffer. */
    if(f->downState==DOWN_WAKE) {
        if(difficulty>0 && f->downTick==0)return KEY_UP;
        return 0;
    }
    if(hitstop)return 0;
    if(f->action)return 0;
    if(f->y)return 0;
    if(f->hurt && !f->guard)return 0;
    forward=f->face?KEY_RIGHT:KEY_LEFT;back=f->face?KEY_LEFT:KEY_RIGHT;
    distance=abs16(f->x-enemy->x)>>4;
    chance=(rng()>>8)&31;
    habit=&cpuPersonalities[f->id];
    enemyActive=0;
    /* Current visible action only: input precedes the attack clock update.
     * This existing tick+1 guard observes no opponent pad or future input. */
    if(enemy->action && enemy->tick+1>=enemy->actionStartup) {
        if(enemy->tick+1<enemy->actionActiveEnd)enemyActive=1;
    }
    /* Incoming-wave priority and reliable Normal/Hard low guard are shared. */
    waveApproaching=0;
    if(waves[0].active && waves[0].face && waves[0].x<f->x)waveApproaching=1;
    if(waves[0].active && !waves[0].face && waves[0].x>f->x)waveApproaching=1;
    if(waveApproaching) {
        waveDistance=abs16(waves[0].x-f->x)>>4;
        if(waveDistance<96) {
            if(waves[0].low) {
                if(difficulty>0 || chance<10)return back|KEY_DOWN;
            } else if(chance<18)return back;
        }
    }
    if(enemyActive && distance<64 && chance<6+difficulty*5+habit->guard)
        return back | (enemy->duck?KEY_DOWN:0);
    if(f->hurt)return 0;
    if(enemy->downState)return 0;
    /* Optional integration point for feature 07: a legal super command may
     * be sampled here after availability/defense, before signature specials.
     * No duplicate meter, command recognizer or super engine belongs here. */
    if(f->energy>=32) {
        if(c->specialFamily==SPECIAL_PROJECTILE || c->specialFamily==SPECIAL_GROUNDWAVE) {
            if(!waves[1].active) {
                if(distance>110 && f->energy>=64)return KEY_DOWN|KEY_Y;
                if(distance>95 && ((frame+f->id*13)%97==0))return KEY_DOWN|KEY_Y;
            }
        } else if((frame+f->id*13)%97==0) {
            if(c->specialFamily==SPECIAL_RUSH) {
                specialMax=c->specialReach+BODY_HALF_WIDTH;
                specialMax+=((u16)c->specialSpeed*c->specialActive)>>4;
                if(specialMax>90)specialMax=90;
                if(distance>=45 && distance<=specialMax)return KEY_DOWN|KEY_Y;
            } else if(c->specialFamily==SPECIAL_RISING) {
                if(distance<=c->specialReach+BODY_HALF_WIDTH &&
                   (enemy->y<0 || enemyActive))return KEY_DOWN|KEY_Y;
            }
        }
    }
    /* Same fallible universal anti-air, height/range/cadence and chance.
     * It can commit to an empty jump or whiff a retreating target. */
    if(difficulty>0) {
        if(!enemy->hurt && distance<=40) {
            if(enemy->y<=-12*16 && enemy->y>=-56*16) {
                if((enemy->x>f->x)==f->face &&
                   (frame+f->id*13)%(difficulty==2?6:10)==0 &&
                   chance<(difficulty==2?24:16))return KEY_DOWN|KEY_X;
            }
        }
    }
    /* Counter habits sample visible recovery, never a future hit/whiff or
     * an unpressed opponent button. Even Hard is capped at 28/32 and five
     * ticks, so recovery can end or spacing can escape before the answer. */
    if(enemy->action && !enemy->hurt && !enemy->y) {
        if(enemy->tick>=enemy->actionActiveEnd && distance<=46) {
            threshold=habit->counter;
            if(difficulty==0)threshold>>=1;
            if(difficulty==2)threshold+=2;
            if(threshold>28)threshold=28;
            if((frame+f->id*13)%(difficulty==0?14:(difficulty==1?9:5))==0 &&
               chance<threshold)return cpuNormalKey(habit->secondary);
        }
    }
    if(distance>46) {
        k=forward;
        if(distance>65 && difficulty>0 && (frame%143==0))k|=KEY_UP;
        return k;
    }
    tempo=habit->tempo+5;
    if(difficulty==1)tempo=habit->tempo;
    if(difficulty==2)tempo=habit->tempo-3;
    if((frame+f->id*13)%tempo==0) {
        if(distance<c->throwRange && difficulty>0 && chance<habit->throws)
            return forward|KEY_X;
        choice=(chance>>1)&3;
        if(chance<16)choice=habit->primary;
        else if(chance<24)choice=habit->secondary;
        k=cpuNormalKey(choice);
        if(choice==3 && (chance&1))k|=KEY_DOWN;
        return k;
    }
    if(distance>habit->spacing) {
        if(chance<habit->pressure)return forward;
    } else if(distance+5<habit->spacing && chance<habit->retreat)return back;
    else if(distance>=29 && chance<(habit->pressure>>1))return forward;
    return 0;
}

#endif
