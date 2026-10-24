#ifndef ABAQUS_TRAINING_TOOLS_H
#define ABAQUS_TRAINING_TOOLS_H

extern u8 trainingVisible,trainingChallenge,trainingResult,trainingRestore;
extern char trainingHistoryText[33],trainingStatusText[33];
extern const char trainingChallengeNames[3][22];
void trainingReset(void);
void trainingNewMatch(void);
void trainingChooseChallenge(void);
void trainingPrepareChallenge(void);
void trainingCapture(u16 keys);
void trainingStarted(u8 player,u8 action);
void trainingContact(u8 attacker,u8 blocked,u8 low,u8 actualDamage);
void trainingMoveContact(u8 action,u8 air,u8 rear,u8 outcome);
void trainingObserve(void);
void trainingMakeStatus(void);
void trainingService(void);

#endif
#ifdef ABAQUS_TRAINING_TOOLS_IMPLEMENTATION

/* Training observer functions do not alter Fighter, Wave, input or rules.
 * The separate contact adapter below specializes existing knockdown stores.
 * Definitions follow all existing globals and guide tables. Explicit initial
 * values keep these in appended .data, preserving even SDK BSS addresses.
 * The live panel reuses footer rows
 * 26/27 (128 bytes); the ordinary HUD remains exactly 320 bytes. Text is
 * cached; snapshot, five token samples and publication run separately. */
u16 trainingHistory[5]={0},trainingHistorySnapshot[5]={0},trainingLastKeys=0;
u16 trainingDamage=0;
u8 trainingVisible=0,trainingChallenge=0,trainingResult=0,trainingNormalLink=0;
u8 trainingHits=0,trainingChain=0,trainingSpecialCue=0;
u8 trainingHistoryDirty=0,trainingHistoryBuild=0,trainingStatusDirty=0,trainingRestore=0;
char trainingHistoryText[33]={0},trainingStatusText[33]={0};
const char trainingResultNames[4][6]={"READY","LINK!","DONE!","RETRY"};
const char trainingChallengeNames[3][22]={
    "HIT CONFIRM", "BLOCK A LOW ATTACK", "AIR KICK CROSS-UP"
};

/* Contact-budget adapter for the two fixed victim indices in combat().
 * Caller proves throwVictim==255; linked victims keep beginKnockdown().
 * applyHitReaction already cleared action/tick, guard, airAction, buffered
 * input and wake input on this unblocked contact. No intervening code can
 * restore them. Retain connected: the second contact of a trade can set it.
 * Fixed indices avoid 816-tcc rebuilding a far pointer for every byte. */
#define BEGIN_UNLINKED_KNOCKDOWN(victim,direction) do { \
    fighters[victim].downState=DOWN_FLIGHT;fighters[victim].downTick=0; \
    fighters[victim].downOwner=255;fighters[victim].downDamage=0; \
    fighters[victim].connected=0;fighters[victim].duck=0;fighters[victim].walking=0; \
    fighters[victim].face=direction; \
    fighters[victim].vx=(direction)?24:-24;fighters[victim].vy=-40; \
    if(!fighters[victim].y)fighters[victim].y=-1; \
    fighters[victim].motion=0;fighters[victim].downbuffer=0; \
} while(0)

/* The caller lends its now-unused HP scratch word for the saturated sum. */
#define TRAINING_PLAYER_HIT(damage) do { \
    trainingHits=fighters[0].combo; \
    if(trainingHits<=1)trainingDamage=damage; \
    else { \
        damage+=trainingDamage; \
        if(damage>999)damage=999; \
        trainingDamage=damage; \
        if(trainingHits>99)trainingHits=99; \
    } \
    trainingChain=1;trainingStatusDirty=1; \
} while(0)

void trainingReset(void) {
    u8 i;
    for(i=0;i<5;i++){trainingHistory[i]=0;trainingHistorySnapshot[i]=0;}
    for(i=0;i<32;i++){trainingHistoryText[i]=' ';trainingStatusText[i]=' ';}
    trainingHistoryText[32]=0;trainingStatusText[32]=0;
    trainingHistoryText[0]='I';trainingHistoryText[1]='N';
    /* These labels and blank cells are immutable until the next reset. */
    trainingStatusText[7]='H';trainingStatusText[12]='D';
    trainingStatusText[14]='S';trainingStatusText[15]='P';trainingStatusText[18]='C';
    trainingLastKeys=0;trainingDamage=0;trainingHits=0;trainingChain=0;
    trainingResult=0;trainingNormalLink=0;trainingSpecialCue=0;
    trainingHistoryDirty=1;trainingHistoryBuild=0;trainingStatusDirty=1;
    trainingRestore=1;
}
void trainingNewMatch(void) {
    trainingVisible=1;trainingChallenge=0;
    trainingReset();
}
void trainingChooseChallenge(void) {
    trainingChallenge++;if(trainingChallenge>=3)trainingChallenge=0;
    trainingResult=0;trainingNormalLink=0;trainingStatusDirty=1;
    trainingPrepareChallenge();
}
void trainingPrepareChallenge(void) {
    /* A selected drill supplies recovery guard, CPU or Stand as appropriate.
     * Difficulty remains the player's choice; PAUSED can override a partner. */
    if(!trainingChallenge)trainingDummy=6;
    else trainingDummy=trainingChallenge==1?4:0;
}
void trainingCapture(u16 keys) {
    keys&=KEY_UP|KEY_DOWN|KEY_LEFT|KEY_RIGHT|ATTACKS;
    if(keys==trainingLastKeys)return;
    trainingLastKeys=keys;
    /* Neutral releases do not evict a motion step. Repeated presses still
     * enter separately because the last physical signature becomes zero. */
    if(!keys)return;
    trainingHistory[0]=trainingHistory[1];trainingHistory[1]=trainingHistory[2];
    trainingHistory[2]=trainingHistory[3];trainingHistory[3]=trainingHistory[4];
    trainingHistory[4]=keys;trainingHistoryDirty=1;
}
void trainingStarted(u8 player,u8 action) {
    /* Production callers already guard mode==2. */
    if(player)return;
    /* Called after the real action accepted its command and energy cost. */
    if(action==7){trainingSpecialCue=90;trainingStatusDirty=1;}
}
void trainingContact(u8 attacker,u8 blocked,u8 low,u8 actualDamage) {
    u16 sum;
    /* Called only by the mode==2 contact hook. Keep the common first hit
     * off the accumulated-damage/clamping path. */
    if(!attacker) {
        if(blocked) {
            if(trainingChain){trainingChain=0;trainingStatusDirty=1;}
            if(trainingChallenge==0 && trainingResult==1) {
                trainingResult=3;trainingNormalLink=0;trainingStatusDirty=1;
            }
        } else {
            trainingHits=fighters[0].combo;
            if(trainingHits<=1)trainingDamage=actualDamage;
            else {
                sum=trainingDamage+actualDamage;
                if(sum>999)sum=999;
                trainingDamage=sum;
                if(trainingHits>99)trainingHits=99;
            }
            trainingChain=1;trainingStatusDirty=1;
        }
    } else if(blocked) {
        if(trainingChallenge==1 && low && fighters[0].duck) {
            trainingResult=2;trainingStatusDirty=1;
        }
    } else {
        if(trainingChain){trainingChain=0;trainingStatusDirty=1;}
        if(trainingResult!=2) {
            trainingResult=3;trainingNormalLink=0;trainingStatusDirty=1;
        }
    }
}
void trainingMoveContact(u8 action,u8 air,u8 rear,u8 outcome) {
    if(trainingResult==2)return;
    if(trainingChallenge==0) {
        if(outcome!=2)return;
        if(trainingNormalLink && fighters[0].combo>1) {
            if(action==3 || action==5) {
                trainingResult=2;trainingNormalLink=0;trainingStatusDirty=1;
                return;
            }
            if(action==7) {
                trainingResult=2;trainingNormalLink=0;trainingStatusDirty=1;
                return;
            }
        }
        if(action && action<7) {
            trainingNormalLink=1;trainingResult=1;trainingStatusDirty=1;
        }
    } else if(trainingChallenge==2 && action==5 && air) {
        trainingResult=3;
        if(rear && outcome==2)trainingResult=2;
        trainingStatusDirty=1;
    }
}
void trainingObserve(void) {
    u8 cue=trainingSpecialCue;
    if(trainingChain) {
        if(!fighters[1].hurt || fighters[1].guard) {
            trainingChain=0;trainingStatusDirty=1;
            if(trainingChallenge==0 && trainingResult==1) {
                trainingResult=3;trainingNormalLink=0;
            }
        }
    }
    if(cue && animationAdvance) {
        trainingSpecialCue=cue-1;
        if(cue==1)trainingStatusDirty=1;
    }
}
void trainingMakeStatus(void) {
    u16 value;
    u8 digit;
    const char *result=trainingResultNames[trainingResult];
    if(trainingChain) {
        trainingStatusText[0]='N';trainingStatusText[1]='O';
        trainingStatusText[2]='W';trainingStatusText[3]=' ';
    } else {
        trainingStatusText[0]='L';trainingStatusText[1]='A';
        trainingStatusText[2]='S';trainingStatusText[3]='T';
    }
    /* Hits <=99 and damage <=999. Bounded subtraction avoids six 16-bit
     * software divides in the live formatter on the pinned 816-tcc. */
    value=trainingHits;digit='0';
    while(value>=10){value-=10;digit++;}
    trainingStatusText[5]=digit;trainingStatusText[6]='0'+value;
    value=trainingDamage;digit='0';
    while(value>=100){value-=100;digit++;}
    trainingStatusText[9]=digit;digit='0';
    while(value>=10){value-=10;digit++;}
    trainingStatusText[10]=digit;trainingStatusText[11]='0'+value;
    trainingStatusText[16]=trainingSpecialCue?'!':'-';
    trainingStatusText[19]='1'+trainingChallenge;
    trainingStatusText[21]=result[0];trainingStatusText[22]=result[1];
    trainingStatusText[23]=result[2];trainingStatusText[24]=result[3];
    trainingStatusText[25]=result[4];
}
void trainingHistoryToken(u8 slot) {
    u16 keys=trainingHistorySnapshot[slot];
    u8 direction=5;
    char *text=trainingHistoryText+2+(slot<<2)+(slot<<1);
    if(keys&KEY_DOWN)direction=2;
    else if(keys&KEY_UP)direction=8;
    if(keys&KEY_LEFT)direction--;
    else if(keys&KEY_RIGHT)direction++;
    text[0]=keys?'0'+direction:'-';
    text[1]=(keys&KEY_Y)?'Y':'-';
    text[2]=(keys&KEY_X)?'X':'-';
    text[3]=(keys&KEY_B)?'B':'-';
    text[4]=(keys&KEY_A)?'A':'-';
}
void trainingService(void) {
    /* Never format a new footer on an attack/knockdown simulation tick.
     * Impact feedback uses an already settled frozen tick; execution cues
     * and history otherwise wait for a neutral gap. Actor DMA still owns
     * vblank and the footer remains queued behind it. */
    if(!hitstop) {
        if(fighters[0].action|fighters[1].action)return;
        if(fighters[0].downState|fighters[1].downState)return;
        if(fighters[0].y|fighters[1].y)return;
        if(fighters[0].landing|fighters[1].landing)return;
        if(fighters[0].hurt|fighters[1].hurt)return;
    }
    if(guideDirty)return;
    if(impactHudPending|impactBannerPending)return;
    if(hudDirty|bannerDirty)return;
    if(trainingRestore) {
        trainingRestore=0;trainingHistoryDirty=1;trainingStatusDirty=1;
        if(!trainingVisible){clearFightHint();return;}
    }
    if(!trainingVisible)return;
    if(trainingStatusDirty) {
        trainingMakeStatus();drawGuideWord(27*64,trainingStatusText);
        trainingStatusDirty=0;footerDirty=1;return;
    }
    if(hitstop)return;
    if(frame&1)return;
    if(!trainingHistoryBuild && trainingHistoryDirty) {
        trainingHistorySnapshot[0]=trainingHistory[0];
        trainingHistorySnapshot[1]=trainingHistory[1];
        trainingHistorySnapshot[2]=trainingHistory[2];
        trainingHistorySnapshot[3]=trainingHistory[3];
        trainingHistorySnapshot[4]=trainingHistory[4];
        trainingHistoryDirty=0;trainingHistoryBuild=1;
        return;
    }
    if(trainingHistoryBuild==6) {
        drawGuideWord(26*64,trainingHistoryText);footerDirty=1;
        trainingHistoryBuild=0;return;
    }
    if(trainingHistoryBuild) {
        trainingHistoryToken(trainingHistoryBuild-1);
        trainingHistoryBuild++;
    }
}

#endif
