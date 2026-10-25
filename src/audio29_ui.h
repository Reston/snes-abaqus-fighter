#ifndef ABAQUS_AUDIO29_UI_H
#define ABAQUS_AUDIO29_UI_H
/* Reuses the guide's three-phase 1472-byte panel and existing VRAM glyphs.
 * A separate early return prevents Training page ownership leaking here. */
void audio29Open(void) {
    v29AudioState[11]=pausePage;
    if(pausePage==AUDIO29_PAGE)v29AudioState[11]=0;
    openPauseGuide(AUDIO29_PAGE);
}
void audio29ToggleMusic(void) {
    if(musicOn)musicOn=0;
    else {
        musicOn=1;
        if(!AUDIO29_MUSIC) {
            AUDIO29_MUSIC=v29AudioState[13];
            v29AudioState[12]=audio29MusicVolumes[AUDIO29_MUSIC];
        }
        audioTargetVolume=audioSpeechTicks?v29AudioState[12]>>1:v29AudioState[12];
    }
}
void audio29DrawLevel(u8 value,u8 row) {
    if(!value)guideWord(19,row,"OFF");
    else if(value==1)guideWord(19,row,"LOW");
    else if(value==2)guideWord(19,row,"MEDIUM");
    else guideWord(19,row,"HIGH");
}
void audio29Draw(void) {
    if(guideBuild==1) {
        fillGuidePanel();guideCenter(6,"SOUND LEVELS");
        guideWord(3,9,"MUSIC");guideWord(3,12,"EFFECTS");guideWord(3,15,"ANNOUNCER");
        guideBuild=2;
    } else if(guideBuild==2) {
        audio29DrawLevel(AUDIO29_MUSIC,9);
        audio29DrawLevel(AUDIO29_EFFECTS,12);
        audio29DrawLevel(AUDIO29_VOICE,15);
        guideWord(1,9+AUDIO29_CURSOR*3,">");
        guideWord(3,18,"UP/DOWN CHOOSE");
        guideWord(3,19,"LEFT/RIGHT CHANGE");guideBuild=3;
    } else if(guideBuild==3) {
        guideWord(3,21,"X PREVIEW  SELECT BACK");
        guideWord(3,23,musicOn?"L MUSIC ON":"L MUSIC OFF");
        guideWord(3,24,stageDepthTable[9]?"R SCENERY STILL":"R SCENERY MOVING");
        guideWord(3,26,"A/START RESUME  B ROSTER");
        guideBuild=0;guideDirty=1;
    }
}
void audio29Keys(u16 keys,u16 directions) {
    u8 level;
    if(directions&KEY_UP) {if(AUDIO29_CURSOR)AUDIO29_CURSOR--;else AUDIO29_CURSOR=2;}
    else if(directions&KEY_DOWN) {AUDIO29_CURSOR++;if(AUDIO29_CURSOR>2)AUDIO29_CURSOR=0;}
    else if(directions&(KEY_LEFT|KEY_RIGHT)) {
        level=v29AudioState[AUDIO29_CURSOR];
        if(directions&KEY_RIGHT){if(level<3)level++;}
        else if(level)level--;
        v29AudioState[AUDIO29_CURSOR]=level;
        if(AUDIO29_CURSOR==0) {
            musicOn=level!=0;v29AudioState[12]=audio29MusicVolumes[level];
            if(level)v29AudioState[13]=level;
            audioTargetVolume=audioSpeechTicks?v29AudioState[12]>>1:v29AudioState[12];
        }
        else if(AUDIO29_CURSOR==2 && !level) {
            audioSpeechTicks=0;audioTargetVolume=v29AudioState[12];
        }
    } else if(keys&KEY_X) {
        if(AUDIO29_CURSOR==2)audioAnnounce(7,42);
        else if(AUDIO29_CURSOR==1)audioCue(4,3);
        return;
    } else if((keys&KEY_L) && !((pad0|pad1)&KEY_R))audio29ToggleMusic();
    else if((keys&KEY_R) && !((pad0|pad1)&KEY_L))stageDepthTable[9]=!stageDepthTable[9];
    else return;
    openPauseGuide(AUDIO29_PAGE);
}
#endif
