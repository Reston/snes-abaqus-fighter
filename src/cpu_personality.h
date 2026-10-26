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
    /* Madariaga: forward strong-kick pressure and throws. */
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
    u16 k=0,forward,back,waveDistance,specialMax,phase;
    u8 chance,enemyActive,waveApproaching,tempo,threshold,choice,specialFamily,spacing,reaction;
    const CharacterProfile *c;
    const CpuPersonality *habit;
    if(mode==2 && trainingDummy!=4)return trainingKeys();
    if(!fighters[1].hp)return 0;
    if(!fighters[0].hp)return 0;
    if(fighters[1].downState==DOWN_LIFT)return defense29CpuKeys();
    if(fighters[1].downState && fighters[1].downState!=DOWN_WAKE)return 0;
    /* The single existing wake edge retains captureInput's six-tick buffer. */
    if(fighters[1].downState==DOWN_WAKE) {
        if(difficulty>0 && fighters[1].downTick==0)return KEY_UP;
        return 0;
    }
    if(hitstop)return 0;
    if(fighters[1].action)return 0;
    if(fighters[1].y)return 0;
    if(fighters[1].hurt && !fighters[1].guard)return 0;
    forward=fighters[1].face?KEY_RIGHT:KEY_LEFT;back=fighters[1].face?KEY_LEFT:KEY_RIGHT;
    distance=abs16(fighters[1].x-fighters[0].x)>>4;
    chance=(rng()>>8)&31;
    habit=&cpuPersonalities[fighters[1].id];
    phase=frame+fighters[1].id*13;
    /* Observe only the current rendered attack clock. New guard decisions
     * sample every 16/12/8 ticks (Easy/Normal/Hard); a guard already held may
     * continue until its visible threat ends. Never read the opponent pad. */
    reaction=phase%(difficulty==0?16:(difficulty==1?12:8))==0;
    if(fighters[1].keys&back)reaction=1;
    enemyActive=0;
    if(fighters[0].action && fighters[0].tick>=fighters[0].actionStartup) {
        if(fighters[0].tick<fighters[0].actionActiveEnd)enemyActive=1;
    }
    /* Incoming-wave priority and reliable Normal/Hard low guard are shared. */
    waveApproaching=0;
    if(waves[0].active && waves[0].face && waves[0].x<fighters[1].x)waveApproaching=1;
    if(waves[0].active && !waves[0].face && waves[0].x>fighters[1].x)waveApproaching=1;
    if(waveApproaching) {
        waveDistance=abs16(waves[0].x-fighters[1].x)>>4;
        if(waveDistance<96 && reaction) {
            if(waves[0].low) {
                if(difficulty>0 || chance<10)return back|KEY_DOWN;
            } else if(chance<18)return back;
        }
    }
    if(reaction && enemyActive && distance<64 && chance<6+difficulty*5+habit->guard)
        return back | (fighters[0].duck?KEY_DOWN:0);
    if(fighters[1].hurt)return 0;
    if(fighters[0].downState)return 0;
    c=combatProfiles[1];
    /* Unsigned phase keeps the original 16-bit wrap, once per decision.
     * Constant-index fighter accesses avoid repeated stack-held far pointers. */
    /* Full-gauge decisions use the same fresh neutral Y+B chord as players.
     * Defense retains priority. Visible range and a fallible sampled chance
     * make commitment readable; no opponent input or future outcome is read. */
    if(difficulty>0 && fighters[1].energy==ENERGY_MAX && !fighters[1].invuln) {
        if(!waves[1].active && !(fighters[1].keys&SUPER_CHORD)) {
            if(chance<(difficulty==2?12:6) && phase%(difficulty==2?53:73)==0) {
                if(superProfiles[fighters[1].id].family==SUPER_VOLLEY) {
                    if(distance>64 && distance<144)return SUPER_CHORD;
                } else if(distance<=superProfiles[fighters[1].id].reach+BODY_HALF_WIDTH-4)return SUPER_CHORD;
            }
        }
    }
    if(fighters[1].energy>=32) {
        specialFamily=c->specialFamily;
        if(specialFamily==SPECIAL_PROJECTILE || specialFamily==SPECIAL_GROUNDWAVE) {
            if(!waves[1].active) {
                if(distance>110 && fighters[1].energy>=64)return KEY_DOWN|KEY_Y;
                if(distance>95 && (phase%97==0))return KEY_DOWN|KEY_Y;
            }
        } else {
            if(specialFamily==SPECIAL_RUSH) {
                if(distance>=45 && distance<=90 && phase%97==0) {
                    specialMax=c->specialReach+BODY_HALF_WIDTH;
                    specialMax+=((u16)c->specialSpeed*c->specialActive)>>4;
                    if(distance<=specialMax)return KEY_DOWN|KEY_Y;
                }
            } else if(specialFamily==SPECIAL_RISING) {
                if(distance<=c->specialReach+BODY_HALF_WIDTH &&
                   (fighters[0].y<0 || enemyActive)) {
                    if(phase%97==0)return KEY_DOWN|KEY_Y;
                }
            }
        }
    }
    /* Same fallible universal anti-air, height/range and chance; slower cadence.
     * It can commit to an empty jump or whiff a retreating target. */
    if(difficulty>0) {
        if(!fighters[0].hurt && distance<=40) {
            if(fighters[0].y<=-12*16 && fighters[0].y>=-56*16) {
                if((fighters[0].x>fighters[1].x)==fighters[1].face &&
                   chance<(difficulty==2?24:16) &&
                   phase%(difficulty==2?14:20)==0)return KEY_DOWN|KEY_X;
            }
        }
    }
    /* Counter habits sample visible recovery, never a future hit/whiff or
     * an unpressed opponent button. Even Hard is capped at 28/32 and sixteen
     * ticks, so recovery can end or spacing can escape before the answer. */
    if(fighters[0].action && !fighters[0].hurt && !fighters[0].y) {
        if(fighters[0].tick>=fighters[0].actionActiveEnd && distance<=46) {
            threshold=habit->counter;
            if(difficulty==0)threshold>>=1;
            if(difficulty==2)threshold+=2;
            if(threshold>28)threshold=28;
            if(chance<threshold &&
               phase%(difficulty==0?28:(difficulty==1?22:16))==0)return cpuNormalKey(habit->secondary);
        }
    }
    if(distance>46) {
        k=forward;
        if(distance>65 && difficulty>0 && (frame%143==0))k|=KEY_UP;
        return k;
    }
    tempo=habit->tempo;
    tempo+=12;
    if(difficulty==0)tempo+=8;
    if(difficulty==2)tempo-=2;
    /* An even period cannot fire on an odd phase. This cheap prefilter
     * retains the exact modulo condition on every possible firing tick. */
    if(!(tempo&1)) {
        if(phase&1)goto cpu_spacing;
    }
    if(phase%tempo==0) {
        if(distance<c->throwRange && difficulty>0 && chance<habit->throws)
            return forward|KEY_X;
        choice=(chance>>1)&3;
        if(chance<16)choice=habit->primary;
        else if(chance<24)choice=habit->secondary;
        k=cpuNormalKey(choice);
        if(choice==3 && (chance&1))k|=KEY_DOWN;
        return k;
    }
cpu_spacing:
    spacing=habit->spacing;
    if(distance>spacing) {
        if(chance<habit->pressure)return forward;
    } else if(distance+5<spacing && chance<habit->retreat)return back;
    else if(distance>=29 && chance<(habit->pressure>>1))return forward;
    return 0;
}

#endif
