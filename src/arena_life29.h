#ifndef ABAQUS_ARENA_LIFE29_H
#define ABAQUS_ARENA_LIFE29_H

/* Four 16x32 spectators and four 16x16 props, all behind the fighters.
 * BG1 tiles 832..879 / word $3400..$36ff. No palette/OBJ/HDMA ownership.
 * One complete spectator is an indivisible 256-byte transfer. Six such
 * transfers converge a phase; combat/actor/UI work always wins the blank.
 * All persistent state is inside this feature's existing 48-byte lease.
 * 0 stage+1; 1 live clock; 2 desired; 3 completed; 4 next chunk (6=idle);
 * 5 in-flight phase; 6 observed supers; 7 reaction life; 8/9 observed HP;
 * 10 KO latch; 11 reaction kind (0/2 impact/4 super/5 KO); 12 may upload;
 * 13 last round number; 14 completed transfer serial; 15 last event;
 * 16..18 event counters (saturating); 19 last uploaded chunk;
 * 20 last uploaded phase (independent of the next queued phase); rest spare.
 * TRACE115=completed phase, 116=live clock, 117=in-flight phase or 255,
 * 118=completed chunks in that phase (0..5). Completion follows actual DMA.
 */
#define ARENA_LIFE29_VRAM 0x3400
#define ARENA_LIFE29_BYTES 256

void arenaLife29Load(u8 which) {
    u8 i;
    for(i=0;i<48;i++)v29ArenaState[i]=0;
    TRACE[115]=0;TRACE[116]=0;TRACE[117]=255;TRACE[118]=0;
    v29ArenaState[4]=6;
    if(which<3)v29ArenaState[0]=which+1;
}

void arenaLife29Event(u8 kind,u8 life) {
    /* A normal contact cannot erase a super/KO reaction. No combat writes. */
    if(kind<v29ArenaState[11] && v29ArenaState[7])return;
    v29ArenaState[11]=kind;v29ArenaState[7]=life;
    v29ArenaState[15]=kind;
    if(kind==2){if(v29ArenaState[16]<255)v29ArenaState[16]++;}
    else if(kind==4){if(v29ArenaState[17]<255)v29ArenaState[17]++;}
    else {if(v29ArenaState[18]<255)v29ArenaState[18]++;}
}

void arenaLife29Tick(void) {
    u8 supers,heavy,ko;
    v29ArenaState[12]=0;
    if(screen!=FIGHT)return;
    if(!v29ArenaState[0])return;
    supers=superActive[0];if(superActive[1])supers|=2;
    heavy=0;ko=0;
    /* Observe direct actor operands, including hits during a frozen sample.
     * Remember them once, then defer animation until hitstop has finished. */
    if(v29ArenaState[8]>fighters[0].hp+7)heavy=1;
    if(v29ArenaState[9]>fighters[1].hp+7)heavy=1;
    if(!fighters[0].hp)ko=1;
    if(!fighters[1].hp)ko=1;
    if(!paused && !stageDepthTable[9] && !intro) {
        if(heavy)arenaLife29Event(2,96);
        if(supers & ~v29ArenaState[6])arenaLife29Event(4,144);
        if(ko && !v29ArenaState[10])arenaLife29Event(5,240);
    }
    v29ArenaState[8]=fighters[0].hp;v29ArenaState[9]=fighters[1].hp;
    v29ArenaState[6]=supers;v29ArenaState[10]=ko;
    if(intro) {
        v29ArenaState[7]=0;v29ArenaState[11]=0;v29ArenaState[2]=0;
        /* Abort a partly published old celebration at a new round. Mark the
         * pool mixed until one fresh six-chunk phase completes after intro. */
        if(v29ArenaState[13]!=roundNumber) {
            v29ArenaState[13]=roundNumber;
            if(v29ArenaState[4]<6)v29ArenaState[3]=255;
            v29ArenaState[4]=6;TRACE[115]=v29ArenaState[3];
            TRACE[117]=255;TRACE[118]=0;
        }
        return;
    }
    if(paused)return;
    if(stageDepthTable[9])return;
    /* Round-end owns its own safe frozen-combat schedule. The KO contact's
     * hitstop byte is retained by the original rules until the next round;
     * it must not suppress the explicitly scheduled celebration forever. */
    if(hitstop && !roundEnd)return;
    if(!animationAdvance)return;
    /* Only actual KO permits celebration during the existing round-end
     * schedule. Timeout is quiet; panel/actor DMAs retain absolute priority. */
    if(roundEnd && !ko)return;
    if(!roundEnd && ko)return;
    v29ArenaState[1]++;
    if(v29ArenaState[7]) {
        v29ArenaState[7]--;
        v29ArenaState[2]=v29ArenaState[11];
        if(v29ArenaState[11]==2) {
            if(v29ArenaState[7]&16)v29ArenaState[2]=3;
        }
    } else {
        v29ArenaState[11]=0;
        v29ArenaState[2]=(v29ArenaState[1]>>6)&1;
    }
    if(v29ArenaState[4]==6 && v29ArenaState[2]!=v29ArenaState[3]) {
        v29ArenaState[5]=v29ArenaState[2];v29ArenaState[4]=0;
    }
    if(v29ArenaState[4]<6)v29ArenaState[12]=1;
    TRACE[116]=v29ArenaState[1];
    TRACE[117]=v29ArenaState[4]<6?v29ArenaState[5]:255;
    TRACE[118]=v29ArenaState[4]<6?v29ArenaState[4]:0;
}

u8 *arenaLife29Source(void) {
    u8 *data;
    u16 offset;
    if(v29ArenaState[0]==1)data=&arena_life29_stage0;
    else if(v29ArenaState[0]==2)data=&arena_life29_stage1;
    else data=&arena_life29_stage2;
    offset=((u16)v29ArenaState[5]<<10)+((u16)v29ArenaState[5]<<9);
    return data+offset+((u16)v29ArenaState[4]<<8);
}

void arenaLife29Completed(void) {
    v29ArenaState[19]=v29ArenaState[4];v29ArenaState[20]=v29ArenaState[5];
    v29ArenaState[14]++;
    v29ArenaState[4]++;
    if(v29ArenaState[4]==6) {
        v29ArenaState[3]=v29ArenaState[5];TRACE[115]=v29ArenaState[3];
        TRACE[117]=255;TRACE[118]=0;
    } else TRACE[118]=v29ArenaState[4];
}

#endif
