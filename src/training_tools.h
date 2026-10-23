#ifndef ABAQUS_TRAINING_TOOLS_H
#define ABAQUS_TRAINING_TOOLS_H

extern u8 trainingVisible,trainingChallenge,trainingResult,trainingRestore;
extern char trainingHistoryText[33],trainingStatusText[33];
extern const char trainingChallengeNames[3][22];
void trainingReset(void);
void trainingNewMatch(void);
void trainingChooseChallenge(void);
void trainingCapture(u16 keys);
void trainingStarted(u8 player,u8 action);
void trainingContact(u8 attacker,u8 blocked,u8 low,u8 actualDamage);
void trainingMoveContact(u8 action,u8 air,u8 rear,u8 outcome);
void trainingObserve(void);
void trainingMakeStatus(void);
void trainingService(void);

#endif
#ifdef ABAQUS_TRAINING_TOOLS_IMPLEMENTATION

/* Training observer only: no writes to Fighter, Wave, input or combat rules.
 * Definitions follow all existing globals and guide tables. Explicit initial
 * values keep these in appended .data, preserving even SDK BSS addresses.
 * The live panel reuses footer rows
 * 26/27 (128 bytes); the ordinary HUD remains exactly 320 bytes. Text is
 * cached and history construction is spread across five quiet samples. */
u16 trainingHistory[5]={0},trainingHistorySnapshot[5]={0},trainingLastKeys=0;
u16 trainingDamage=0;
u8 trainingVisible=0,trainingChallenge=0,trainingResult=0,trainingNormalLink=0;
u8 trainingHits=0,trainingChain=0,trainingSpecialCue=0;
u8 trainingHistoryDirty=0,trainingHistoryBuild=0,trainingStatusDirty=0,trainingRestore=0;
char trainingHistoryText[33]={0},trainingStatusText[33]={0};
const char trainingResultNames[4][6]={"READY","LINK!","DONE!","RETRY"};
const char trainingChallengeNames[3][22]={
    "NORMAL -> SPECIAL", "BLOCK A LOW ATTACK", "AIR KICK CROSS-UP"
};

void trainingReset(void) {
    u8 i;
    for(i=0;i<5;i++){trainingHistory[i]=0;trainingHistorySnapshot[i]=0;}
    for(i=0;i<32;i++){trainingHistoryText[i]=' ';trainingStatusText[i]=' ';}
    trainingHistoryText[32]=0;trainingStatusText[32]=0;
    trainingHistoryText[0]='I';trainingHistoryText[1]='N';
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
    if(mode!=2)return;
    if(player)return;
    /* Called after the real action accepted its command and energy cost. */
    if(action==7){trainingSpecialCue=90;trainingStatusDirty=1;}
}
void trainingContact(u8 attacker,u8 blocked,u8 low,u8 actualDamage) {
    u16 sum;
    if(mode!=2)return;
    if(!attacker) {
        if(blocked) {
            if(trainingChain){trainingChain=0;trainingStatusDirty=1;}
            if(trainingChallenge==0 && trainingResult==1) {
                trainingResult=3;trainingNormalLink=0;trainingStatusDirty=1;
            }
        } else {
            if(fighters[0].combo<=1)trainingDamage=0;
            sum=trainingDamage+actualDamage;trainingDamage=sum>999?999:sum;
            trainingHits=fighters[0].combo;
            if(trainingHits>99)trainingHits=99;
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
        if(action>=1 && action<=6) {
            trainingNormalLink=1;trainingResult=1;trainingStatusDirty=1;
        } else if(action==7 && trainingNormalLink && fighters[0].combo>1) {
            trainingResult=2;trainingNormalLink=0;trainingStatusDirty=1;
        }
    } else if(trainingChallenge==2 && action==5 && air) {
        trainingResult=3;
        if(rear && outcome==2)trainingResult=2;
        trainingStatusDirty=1;
    }
}
void trainingObserve(void) {
    if(trainingChain) {
        if(!fighters[1].hurt || fighters[1].guard) {
            trainingChain=0;trainingStatusDirty=1;
            if(trainingChallenge==0 && trainingResult==1) {
                trainingResult=3;trainingNormalLink=0;
            }
        }
    }
    if(animationAdvance && trainingSpecialCue) {
        trainingSpecialCue--;
        if(!trainingSpecialCue)trainingStatusDirty=1;
    }
}
void trainingMakeStatus(void) {
    u8 i;
    const char *s=trainingChain?"NOW ":"LAST";
    for(i=0;i<32;i++)trainingStatusText[i]=' ';
    for(i=0;i<4;i++)trainingStatusText[i]=s[i];
    trainingStatusText[5]='0'+trainingHits/10;
    trainingStatusText[6]='0'+trainingHits%10;trainingStatusText[7]='H';
    trainingStatusText[9]='0'+trainingDamage/100;
    trainingStatusText[10]='0'+(trainingDamage/10)%10;
    trainingStatusText[11]='0'+trainingDamage%10;trainingStatusText[12]='D';
    trainingStatusText[14]='S';trainingStatusText[15]='P';
    trainingStatusText[16]=trainingSpecialCue?'!':'-';
    trainingStatusText[18]='C';trainingStatusText[19]='1'+trainingChallenge;
    for(i=0;i<5;i++)trainingStatusText[21+i]=trainingResultNames[trainingResult][i];
}
void trainingHistoryToken(u8 slot) {
    u16 keys=trainingHistorySnapshot[slot];
    u8 x=2+slot*6,direction=5;
    if(keys&KEY_DOWN)direction=2;
    else if(keys&KEY_UP)direction=8;
    if(keys&KEY_LEFT)direction--;
    else if(keys&KEY_RIGHT)direction++;
    trainingHistoryText[x]=keys?'0'+direction:'-';
    trainingHistoryText[x+1]=(keys&KEY_Y)?'Y':'-';
    trainingHistoryText[x+2]=(keys&KEY_X)?'X':'-';
    trainingHistoryText[x+3]=(keys&KEY_B)?'B':'-';
    trainingHistoryText[x+4]=(keys&KEY_A)?'A':'-';
}
void trainingService(void) {
    u8 i;
    if(guideDirty)return;
    if(impactHudPending || impactBannerPending)return;
    if(hudDirty || bannerDirty)return;
    /* Never format a new footer on an attack/knockdown simulation tick.
     * Impact feedback uses an already settled frozen tick; execution cues
     * and history otherwise wait for a neutral gap. Actor DMA still owns
     * vblank and the footer remains queued behind it. */
    if(!hitstop) {
        if(fighters[0].action || fighters[1].action)return;
        if(fighters[0].downState || fighters[1].downState)return;
        if(fighters[0].y || fighters[1].y)return;
        if(fighters[0].landing || fighters[1].landing)return;
        if(fighters[0].hurt || fighters[1].hurt)return;
    }
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
        for(i=0;i<5;i++)trainingHistorySnapshot[i]=trainingHistory[i];
        trainingHistoryDirty=0;trainingHistoryBuild=1;
    }
    if(trainingHistoryBuild) {
        trainingHistoryToken(trainingHistoryBuild-1);
        trainingHistoryBuild++;
        if(trainingHistoryBuild==6) {
            drawGuideWord(26*64,trainingHistoryText);footerDirty=1;
            trainingHistoryBuild=0;
        }
    }
}

#endif
